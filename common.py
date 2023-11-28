import shlex


def print_cmd(args):
    cmd = " ".join(shlex.quote(arg) for arg in args)
    print("$ " + cmd)
