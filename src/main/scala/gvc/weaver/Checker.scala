package gvc.weaver

import gvc.transformer.IRGraph._
import Collector._

object Checker {
  def insert(program: CollectedProgram): Unit = {
    program.methods.values.foreach { method => insert(program.program, method) }
  }

  private def insert(program: Program, collected: CollectedMethod): Unit = {
    val method = collected.method

    // `ops` is a function that generates the operations, given the current return value at that
    // position. DO NOT construct the ops before passing them to this method since multiple copies
    // may be required.
    def insertAt(at: Location, ops: Option[Expression] => Seq[Op]): Unit = at match {
      case Invariant(op) => ???
      case Pre(op) => op.insertBefore(ops(None))
      case Post(op) => op.insertAfter(ops(None))
      case MethodPre => ops(None).foreach(_ +=: method.body)
      case MethodPost => {
        collected.returns.foreach(e => e.insertBefore(ops(e.value)))
        if (collected.hasImplicitReturn) {
          ops(None).foreach(method.body += _)
        }
      }
    }

    // Define condition variables and create a map from term ID to variables
    val conditions = collected.conditions
      .map(cond => (cond.id, method.addVar(BoolType, s"_cond_${cond.id}")))
      .toMap

    def getConjunction(conj: Conjunction): Option[Expression] =
      conj.values.foldLeft[Option[Expression]](None) {
        case (expr, (cond, flag)) => {
          val variable = conditions(cond.id)
          val value = if (flag) variable else new Unary(UnaryOp.Not, variable)
          expr match {
            case None => Some(value)
            case Some(expr) => Some(new Binary(BinaryOp.And, expr, value))
          }
        }
      }

    def getDisjunction(disj: Disjunction): Option[Expression] =
      disj.cases.foldLeft[Option[Expression]](None) {
        case (Some(expr), conj) => getConjunction(conj).map(new Binary(BinaryOp.Or, expr, _))
        case (None, conj) => getConjunction(conj)
      }

    def getConditionValue(cond: Condition): Expression = getDisjunction(cond.when) match {
      case None => cond.value.toIR(program, method, None)
      case Some(when) => new Binary(BinaryOp.And, when, cond.value.toIR(program, method, None))
    }

    // Insert the required assignments to condition variables
    collected.conditions.foreach { cond =>
      insertAt(cond.location, _ => Seq(new Assign(conditions(cond.id), getConditionValue(cond))))
    }

    def implementCheck(check: Check, returnValue: Option[Expression]): Op = check match {
      case AccessibilityCheck(field) => ???
      case expr: CheckExpression =>
        new Assert(
          expr.toIR(program, method, returnValue),
          AssertKind.Imperative)
    }

    def implementChecks(
      cond: Option[Expression],
      checks: Seq[Check],
      returnValue: Option[Expression]
    ): Seq[Op] = {
      val ops = checks.map(implementCheck(_, returnValue))
      cond match {
        case None => ops
        case Some(cond) => {
          val iff = new If(cond)
          iff.condition = cond
          ops.foreach(iff.ifTrue += _)
          Seq(iff)
        }
      }
    }

    // Insert the runtime checks
    // Group them by location and condition, so that multiple checks can be contained in a single
    // if block.
    collected.checks.groupBy(c => (c.location, c.when))
      .foreach {
        case ((loc, when), checks) => {
          val condition = getDisjunction(when)
          insertAt(loc, implementChecks(condition, checks.map(_.check), _))
        }
      }
  }
}
