import sys, traceback

def run_user_code(envdir):
    source = input(">>> ")
    try:
        exec(source, envdir)
    except Exception:
        print("Exception in user code:")
        print("-"*60)
        traceback.print_exc(file=sys.stdout)
        print("-"*60)

envdir = {}
while True:
    run_user_code(envdir)

# Note
'''
>>> "print('Hi')"
Hi
>>>

>>> "a = 5\nb = 6\nc = a + b\nprint(c)"
11
>>> 
'''
