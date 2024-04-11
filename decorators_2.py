from functools import wraps

def my_decorator(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        print('before the function')
        return_value = func(*args, **kwargs)
        print('after the function')
        return return_value
    return wrapper

@my_decorator
def shout_out(shout_value):
    return shout_value.upper()

@my_decorator
def whisper_it(whisper_value):
    print(whisper_value.lower())

print(shout_out('hello'))
whisper_it('goodbye')