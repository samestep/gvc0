package gvc.weaver
import gvc.transformer.IRGraph._
import Collector._
import gvc.transformer.{IRGraph, SilverVarId}
import scala.collection.mutable
import scala.annotation.tailrec

object Checker {
  type StructIDTracker = Map[scala.Predef.String, StructField]

  class CheckerMethod(
      val method: Method,
      tempVars: Map[SilverVarId, Invoke]
  ) extends CheckMethod {
    val resultVars = mutable.Map[java.lang.String, Expression]()

    def resultVar(name: java.lang.String): Expression = {
      resultVars.getOrElseUpdate(
        name, {
          val invoke = tempVars.getOrElse(
            SilverVarId(method.name, name),
            throw new WeaverException(s"Missing temporary variable '$name'")
          )

          invoke.target.getOrElse {
            val retType = invoke.method.returnType.getOrElse(
              throw new WeaverException(
                s"Invalid temporary variable '$name' for void '${invoke.callee.name}'"
              )
            )

            val tempVar = method.addVar(retType)
            invoke.target = Some(tempVar)
            tempVar
          }
        }
      )
    }
  }

  def insert(program: CollectedProgram): Unit = {
    val runtime = CheckRuntime.addToIR(program.program)

    // Add the _id field to each struct
    // Keep a separate map since the name may be something other than `_id` due
    // to name collision avoidance
    val structIdFields = program.program.structs
      .map(s => (s.name, s.addField(CheckRuntime.Names.id, IntType)))
      .toMap

    val implementation =
      new CheckImplementation(program.program, runtime, structIdFields)

    program.methods.values.foreach { method =>
      insert(program, method, runtime, implementation)
    }
  }

  private def insert(
      programData: CollectedProgram,
      methodData: CollectedMethod,
      runtime: CheckRuntime,
      implementation: CheckImplementation
  ): Unit = {
    val program = programData.program
    val method = methodData.method
    val checkMethod = new CheckerMethod(method, programData.temporaryVars)

    // `ops` is a function that generates the operations, given the current return value at that
    // position. DO NOT construct the ops before passing them to this method since multiple copies
    // may be required.
    def insertAt(at: Location, ops: Option[Expression] => Seq[Op]): Unit =
      at match {
        case LoopStart(op: While) => ops(None) ++=: op.body
        case LoopEnd(op: While)   => op.body ++= ops(None)
        case Pre(op)              => op.insertBefore(ops(None))
        case Post(op)             => op.insertAfter(ops(None))
        case MethodPre            => ops(None) ++=: method.body
        case MethodPost =>
          methodData.returns.foreach(e => e.insertBefore(ops(e.value)))
          if (methodData.hasImplicitReturn) {
            method.body ++= ops(None)
          }
        case _ => throw new WeaverException(s"Invalid location '$at'")
      }

    var nextConditionalId = 1
    val conditionVars = methodData.conditions.map { c =>
      val flag = method.addVar(BoolType, s"_cond_$nextConditionalId")
      nextConditionalId += 1
      c -> flag
    }.toMap

    def foldConditionList(conds: List[Condition], op: IRGraph.BinaryOp): Expression = {
      conds.foldLeft[Option[Expression]](None) {
        case (Some(expr), cond) =>
          Some(new Binary(op, expr, getCondition(cond)))
        case (None, cond) => Some(getCondition(cond))
      }.getOrElse(throw new WeaverException("Invalid empty condition list"))
    }

    def getCondition(cond: Condition): Expression = cond match {
      case ImmediateCondition(expr) => expr.toIR(program, checkMethod, None)
      case cond: TrackedCondition => conditionVars(cond)
      case NotCondition(value) => new Unary(UnaryOp.Not, getCondition(value))
      case AndCondition(values) => foldConditionList(values, IRGraph.BinaryOp.And)
      case OrCondition(values) => foldConditionList(values, IRGraph.BinaryOp.Or)
    }

    val initializeOps = mutable.ListBuffer[Op]()

    var (primaryOwnedFields, instanceCounter) = methodData.callStyle match {
      case MainCallStyle => {
        val instanceCounter =
          method.addVar(
            new PointerType(IntType),
            CheckRuntime.Names.instanceCounter
          )
        initializeOps += new AllocValue(IntType, instanceCounter)
        (None, instanceCounter)
      }

      case PreciseCallStyle => {
        val instanceCounter =
          method.addParameter(
            new PointerType(IntType),
            CheckRuntime.Names.instanceCounter
          )
        (None, instanceCounter)
      }

      case ImpreciseCallStyle | PrecisePreCallStyle => {
        val ownedFields: Var =
          method.addParameter(
            runtime.ownedFieldsRef,
            CheckRuntime.Names.primaryOwnedFields
          )
        val instanceCounter =
          new FieldMember(ownedFields, runtime.ownedFieldInstanceCounter)
        (Some(ownedFields), instanceCounter)
      }
    }

    def getPrimaryOwnedFields(): Var = primaryOwnedFields.getOrElse {
      val ownedFields = method.addVar(
        runtime.ownedFieldsRef,
        CheckRuntime.Names.primaryOwnedFields
      )
      primaryOwnedFields = Some(ownedFields)

      initializeOps += new Invoke(
        runtime.initOwnedFields,
        List(instanceCounter),
        primaryOwnedFields
      )
      ownedFields
    }

    // Insert the runtime checks
    // Group them by location and condition, so that multiple checks can be contained in a single
    // if block.
    val context = CheckContext(program, checkMethod, implementation, runtime)
    naiveGrouping(methodData.checks)
      .foreach { case (loc, when, checks) =>
        val condition = when.map(getCondition(_))
        insertAt(
          loc,
          implementChecks(
            condition,
            checks.map(_.check),
            _,
            getPrimaryOwnedFields,
            instanceCounter,
            context
          )
        )
      }

    val needsToTrackPrecisePerms =
      primaryOwnedFields.isDefined ||
        methodData.calls.exists(c => (
          c.ir.callee.isInstanceOf[Method] &&
          (programData.methods(c.ir.callee.name).callStyle match {
            case ImpreciseCallStyle | PrecisePreCallStyle => true
            case _                                        => false
          })
        ))

    // Update the call sites to add any required parameters
    for (call <- methodData.calls) {
      call.ir.callee match {
        case _: DependencyMethod => ()
        case callee: Method =>
          val calleeData = programData.methods(callee.name)
          calleeData.callStyle match {
            // No parameters can be added to a main method
            case MainCallStyle => ()

            // Imprecise methods always get the primary owned fields instance directly
            case ImpreciseCallStyle => call.ir.arguments :+= getPrimaryOwnedFields

            case PreciseCallStyle => {
              // Always pass the instance counter
              call.ir.arguments :+= instanceCounter

              // If we need to track precise permissons, add the code at the call site
              if (needsToTrackPrecisePerms) {
                // Convert precondition into calls to removeAcc
                val context = new CallSiteContext(call.ir, method)
                call.ir.insertBefore(
                  callee.precondition.toSeq.flatMap(
                    implementation.translate(
                      RemoveMode,
                      _,
                      getPrimaryOwnedFields,
                      context
                    )
                  )
                )

                // Convert postcondition into calls to addAcc
                call.ir.insertAfter(
                  callee.postcondition.toSeq.flatMap(
                    implementation.translate(
                      AddMode,
                      _,
                      getPrimaryOwnedFields,
                      context
                    )
                  )
                )
              }
            }

            // For precise-pre/imprecise-post, create a temporary set of permissions, add the
            // permissions from the precondition, call the method, and add the temporary set to the
            // primary set
            case PrecisePreCallStyle => {
              val tempSet = method.addVar(
                runtime.ownedFieldsRef,
                CheckRuntime.Names.temporaryOwnedFields
              )

              val createTemp = new Invoke(
                runtime.initOwnedFields,
                List(instanceCounter),
                Some(tempSet)
              )

              val context = new CallSiteContext(call.ir, method)

              val addPermsToTemp = callee.precondition.toSeq
                .flatMap(
                  implementation.translate(AddMode, _, tempSet, context)
                )
                .toList
              val removePermsFromPrimary = callee.precondition.toSeq
                .flatMap(
                  implementation.translate(
                    RemoveMode,
                    _,
                    getPrimaryOwnedFields,
                    context
                  )
                )
                .toList

              call.ir.insertBefore(
                createTemp :: addPermsToTemp ++ removePermsFromPrimary
              )
              call.ir.arguments :+= tempSet
              call.ir.insertAfter(
                new Invoke(
                  runtime.join,
                  List(getPrimaryOwnedFields, tempSet),
                  None
                )
              )
            }
          }
      }
    }

    // If a primary owned fields instance is required for this method, add all allocations into it
    addAllocationTracking(
      primaryOwnedFields,
      instanceCounter,
      methodData.allocations,
      implementation,
      runtime
    )

    // Add all conditions that need tracked
    // Group all conditions for a single location and insert in sequence
    // to preserve the correct ordering of conditions.
    methodData.conditions
      .groupBy(_.location)
      .foreach {
        case (loc, conds) => insertAt(loc, retVal => {
          conds.map(c => new Assign(conditionVars(c), c.value.toIR(program, checkMethod, retVal)))
        })
    }

    // Finally, add all the initialization ops to the beginning
    initializeOps ++=: method.body
  }

  def addAllocationTracking(
      primaryOwnedFields: Option[Var],
      instanceCounter: Expression,
      allocations: List[Op],
      implementation: CheckImplementation,
      runtime: CheckRuntime
  ): Unit = {
    for (alloc <- allocations) {
      alloc match {
        case alloc: AllocStruct => primaryOwnedFields match {
          case Some(primary) => implementation.trackAllocation(alloc, primary)
          case None => implementation.idAllocation(alloc, instanceCounter)
        }
        case _ =>
          throw new WeaverException(
            "Tracking is only currently supported for struct allocations."
          )
      }
    }
  }

  def implementAccCheck(
      check: FieldPermissionCheck,
      fields: FieldCollection,
      context: CheckContext
  ): Seq[Op] = {
    val field = check.field.toIR(context.program, context.method, None)
    val (mode, perms) = check match {
      case _: FieldSeparationCheck =>
        (SeparationMode, fields.temporaryOwnedFields())
      case _: FieldAccessibilityCheck =>
        (VerifyMode, fields.primaryOwnedFields())
    }
    context.implementation.translateFieldPermission(mode, field, perms, ValueContext)
  }

  def implementPredicateCheck(
      check: PredicatePermissionCheck,
      returnValue: Option[Expression],
      fields: FieldCollection,
      context: CheckContext
  ): Seq[Op] = {
    val instance = new PredicateInstance(
      context.program.predicate(check.predicateName),
      check.arguments.map(_.toIR(context.program, context.method, returnValue))
    )
    val (mode, perms) = check match {
      case _: PredicateSeparationCheck =>
        (SeparationMode, fields.temporaryOwnedFields())
      case _: PredicateAccessibilityCheck =>
        (VerifyMode, fields.primaryOwnedFields())
    }
    context.implementation.translatePredicateInstance(mode, instance, perms, ValueContext)
  }

  case class FieldCollection(
      primaryOwnedFields: () => Var,
      temporaryOwnedFields: () => Var
  )

  case class CheckContext(
      program: Program,
      method: CheckMethod,
      implementation: CheckImplementation,
      runtime: CheckRuntime
  )

  def implementCheck(
      check: Check,
      returnValue: Option[IRGraph.Expression],
      fields: FieldCollection,
      context: CheckContext
  ): Seq[Op] = {
    check match {
      case acc: FieldPermissionCheck =>
        implementAccCheck(
          acc,
          fields,
          context
        )
      case pc: PredicatePermissionCheck =>
        implementPredicateCheck(
          pc,
          returnValue,
          fields,
          context
        )
      case expr: CheckExpression =>
        Seq(
          new Assert(
            expr.toIR(context.program, context.method, returnValue),
            AssertKind.Imperative
          )
        )
    }
  }

  def implementChecks(
      cond: Option[Expression],
      checks: List[Check],
      returnValue: Option[Expression],
      getPrimaryOwnedFields: () => Var,
      instanceCounter: Expression,
      context: CheckContext
  ): Seq[Op] = {
    // Create a temporary owned fields instance when it is required
    var temporaryOwnedFields: Option[Var] = None
    def getTemporaryOwnedFields(): Var = temporaryOwnedFields.getOrElse {
      val tempVar = context.method.method.addVar(
        context.runtime.ownedFieldsRef,
        CheckRuntime.Names.temporaryOwnedFields
      )
      temporaryOwnedFields = Some(tempVar)
      tempVar
    }
    // Collect all the ops for the check
    var ops =
      checks.flatMap(
        implementCheck(
          _,
          returnValue,
          FieldCollection(getPrimaryOwnedFields, getTemporaryOwnedFields),
          context
        )
      )

    // Prepend op to initialize owned fields if it is required
    temporaryOwnedFields.foreach { tempOwned =>
      ops = new Invoke(
        context.runtime.initOwnedFields,
        List(instanceCounter),
        Some(tempOwned)
      ) :: ops
    }

    // Wrap in an if statement if it is conditional
    cond match {
      case None => ops
      case Some(cond) =>
        val iff = new If(cond)
        iff.condition = cond
        ops.foreach(iff.ifTrue += _)
        Seq(iff)
    }
  }

  // TODO: Finish up a proper ordering strategy for checks that uses the following method instead of this
  def naiveGrouping(items: List[RuntimeCheck]): List[(Location, Option[Condition], List[RuntimeCheck])] = {
    items.groupBy(i => (i.location, i.when))
      .map { case ((loc, when), checks) => (loc, when, checks) }
      .toList
  }

  def groupChecks(items: List[RuntimeCheck]): List[(Location, Option[Condition], List[RuntimeCheck])] = {
    items.groupBy(_.location)
      .toList
      .flatMap { case (loc, checks) =>
        val groups = groupConditions(checks)
        val sorted = orderChecks(groups)
        groupAdjacentConditions(sorted).map { case (cond, checks) => (loc, cond, checks) }
      }
  }

  // Groups conditions but does not change order
  @tailrec
  def groupAdjacentConditions(
      items: List[RuntimeCheck],
      acc: List[(Option[Condition], List[RuntimeCheck])] = Nil
  ): List[(Option[Condition], List[RuntimeCheck])] = {
    items match {
      case Nil => acc
      case head :: rest => {
        val (same, remaining) = rest.span(_.when == head.when)
        groupAdjacentConditions(remaining, acc :+ (head.when, head :: same))
      }
    }
  }

  // Groups conditions in a stable-sort manner (the first items in each group are in order, etc.),
  // but allows ordering changes
  def groupConditions(items: List[RuntimeCheck]): List[RuntimeCheck] = {
    val map = mutable.LinkedHashMap[Option[Condition], mutable.ListBuffer[RuntimeCheck]]()
    for (check <- items) {
      val list = map.getOrElseUpdate(check.when, mutable.ListBuffer())
      list += check
    }

    map.flatMap { case (_, checks) => checks }
      .toList
  }

  def orderChecks(checks: List[RuntimeCheck]) =
    checks.sortBy(c => c.check match {
      case acc: FieldAccessibilityCheck => nesting(acc.field)
      case _ => 0
    })(Ordering.Int.reverse)

  def nesting(expr: CheckExpression): scala.Int = expr match {
    case b: CheckExpression.Binary =>
      Math.max(nesting(b.left), nesting(b.right)) + 1
    case c: CheckExpression.Cond =>
      Math.max(nesting(c.cond), Math.max(nesting(c.ifTrue), nesting(c.ifFalse))) + 1
    case d: CheckExpression.Deref =>
      nesting(d.operand) + 1
    case f: CheckExpression.Field =>
      nesting(f.root) + 1
    case u: CheckExpression.Unary =>
      nesting(u.operand) + 1
    case _: CheckExpression.Literal
      | _: CheckExpression.Var
      | CheckExpression.Result
      | _: CheckExpression.ResultVar => 1
  }
}
