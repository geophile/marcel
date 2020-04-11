class Base:

    @classmethod
    def m(cls):
        print(f'm Base {cls}')

    @classmethod
    def n(cls):
        print(f'n Base {cls}')


class Sub(Base):

    @classmethod
    def m(cls):
        print(f'm Sub {cls}')


x = Base()
x.m()
x.n()
x = Sub()
x.m()
x.n()
