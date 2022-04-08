"""
aiml/tests/test_eval.py
"""

def main():
    code = """\
m+
"""
    try:
        eval(code)
    except Exception as e:
        print(e)

if __name__ == '__main__':
    main()