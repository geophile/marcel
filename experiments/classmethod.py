class Base:

    @classmethod
    def m(cls):
        """
        Èi̇·åıĸæńį¢æīĸ

        Args:
            cls: (todo): write your description
        """
        print(f'm Base {cls}')

    @classmethod
    def n(cls):
        """
        Èi̇ ]

        Args:
            cls: (todo): write your description
        """
        print(f'n Base {cls}')


class Sub(Base):

    @classmethod
    def m(cls):
        """
        Èi̇·åıĸæńį¢æīĸ

        Args:
            cls: (todo): write your description
        """
        print(f'm Sub {cls}')


x = Base()
x.m()
x.n()
x = Sub()
x.m()
x.n()
