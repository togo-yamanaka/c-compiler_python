"""
Parserクラス
"""


from __future__ import annotations
from tokenizer import TokenKind, TokenOperator
from enum import IntEnum, auto
from typing import List, Union


class NodeKind(IntEnum):
    """ノード種別を表す"""

    ADD = auto()  # +
    SUB = auto()  # -
    MUL = auto()  # *
    DIV = auto()  # /
    GREATER = auto()  # >
    GREATER_EQUAL = auto()  # >=
    LOWER = auto()  # <
    LOWER_EQUAL = auto()  # <=
    EQUAL = auto()  # ==
    NOT_EQUAL = auto()  # !=
    ASSIGN = auto()  # =
    LOCAL_VAR = auto()  # LOCAL VARIABLE
    NUMBER = auto()  # NUMBER


class Node:
    """抽象構文木クラス"""

    def __init__(self):
        """初期化"""
        self.value: Union[int, str, None] = None
        self.kind: Union[NodeKind, None] = None
        self.offset: Union[int, None] = None
        self.left_hand: Union[Node, None] = None
        self.right_hand: Union[Node, None] = None

    def __repr__(self) -> str:
        """文字列型表示を定義"""
        return f"""
        Node(value={self.value}, kind={str(NodeKind(self.kind))}, offset={self.offset},
        left_hand={getattr(self.left_hand, "value", None)},
        right_hand={getattr(self.right_hand, "value", None)})
        """


class LocalVariable:
    """ローカル変数を表すクラス"""

    def __init__(self, name: Union[str, None] = None, offset: Union[int, None] = None):
        self.next: Union[LocalVariable, None] = None
        self.name = name
        self.offset = offset


class LocalVariableOperator:
    """LocalVariableを操作するクラス"""

    def __init__(self):
        self.head = LocalVariable()
        self.cursor = self.head.next

    def get_offset(self) -> int:
        """現在指しているカーソルノードのoffsetを取得する"""
        try:
            return self.cursor.offset
        except AttributeError:
            raise AttributeError("連結リストにノードが存在しません")

    def proceed_pointer(self) -> None:
        """ポインターを一つ進める"""
        try:
            next_node = self.cursor.next
            if next_node is None:
                raise AttributeError("ポインターが指すノードの次のノードがありません")
            self.cursor = next_node
        except AttributeError:
            raise AttributeError("連結リストにノードが1つも存在していません")

    def find(self, value: str) -> LocalVariable:
        """
        valueの値をもつLocalVariableオブジェクトが存在するか確認する

        存在しない場合はエラーを起こす
        """
        pointer = self.head.next
        while pointer:
            if pointer.name == value:
                return pointer
            pointer = pointer.next

        raise LookupError(f"{value}はローカル変数としてアサインされていません")


class Parser:
    """文字列を読み取りノード(抽象構文木)を作成する"""

    def __init__(self, cursor: TokenOperator) -> None:
        """カーソルを設定する"""
        self.cursor = cursor
        self.local_var_cursor = LocalVariableOperator()

    def create_new_node(
        self,
        value: Union[str, int, None],
        kind: NodeKind,
        left_hand: Union[Node, None] = None,
        right_hand: Union[Node, None] = None,
    ) -> Node:
        """新たノードを作成する"""
        node = Node()
        node.value = value
        node.kind = kind
        node.right_hand = right_hand
        node.left_hand = left_hand
        return node

    def create_new_local_var_node(self, name: str):
        """
        ローカル変数ノードを抽象構文木に追加する

        副作用としてローカル変数ノードの操作も行う
        """
        try:
            target_local_var_node = self.local_var_cursor.find(name)
            target_offset = target_local_var_node.offset
        except LookupError:
            if self.local_var_cursor.cursor is None:
                target_offset = 8
                self.local_var_cursor.head.next = LocalVariable(name=name, offset=target_offset)
                self.local_var_cursor.cursor = self.local_var_cursor.head.next
            else:
                target_offset = self.local_var_cursor.get_offset() + 8
                self.local_var_cursor.cursor.next = LocalVariable(name=name, offset=target_offset)
                self.local_var_cursor.proceed_pointer()

        node = self.create_new_node(value=name, kind=NodeKind.LOCAL_VAR)
        node.offset = target_offset

        return node

    def run(self) -> List[Node]:
        """パーサの実行"""
        nodes = self.program(self.cursor)

        if self.cursor.chack_type(TokenKind.EOF) is False:
            raise IndexError("パース出来ていないトークンが存在します")

        return nodes

    def program(self, cursor: TokenOperator) -> List[Node]:
        """
        program具象構文木

        program = statement*
        """
        nodes = []
        while cursor.chack_type(TokenKind.EOF) is False:
            nodes.append(self.statement(cursor))

        return nodes

    def statement(self, cursor: TokenOperator) -> Node:
        """
        statement具象構文木

        statement = expression ";"
        """
        node = self.expression(cursor)

        if cursor.consume(";") is False:
            raise ValueError("プログラムの末尾が;で終わっていません")

        return node

    def expression(self, cursor: TokenOperator) -> Node:
        """expression具象構文木"""
        return self.assign(cursor)

    def assign(self, cursor: TokenOperator) -> Node:
        """
        assign具象構文木

        assign = equality ("=" assign)?
        """
        node = self.equality(cursor)

        if cursor.consume("="):
            node = self.create_new_node("=", NodeKind.ASSIGN, node, self.assign(cursor))

        return node

    def equality(self, cursor: TokenOperator) -> Node:
        """
        equality具象構文木

        equality = relation ("==" relation | "!=" relation)*
        """
        node = self.relation(cursor)

        while 1:
            if cursor.consume("=="):
                node = self.create_new_node("==", NodeKind.EQUAL, node, self.relation(cursor))
            elif cursor.consume("!="):
                node = self.create_new_node("!=", NodeKind.NOT_EQUAL, node, self.relation(cursor))
            else:
                return node

    def relation(self, cursor: TokenOperator) -> Node:
        """
        relation具象構文木

        relation = add ("<" add | "<=" add | ">" add | ">=" add )*
        """
        node = self.add(cursor)

        while 1:
            if cursor.consume(">="):
                node = self.create_new_node(">=", NodeKind.GREATER_EQUAL, node, self.add(cursor))
            elif cursor.consume(">"):
                node = self.create_new_node(">", NodeKind.GREATER, node, self.add(cursor))
            elif cursor.consume("<="):
                node = self.create_new_node("<=", NodeKind.LOWER_EQUAL, node, self.add(cursor))
            elif cursor.consume("<"):
                node = self.create_new_node("<", NodeKind.LOWER, node, self.add(cursor))
            else:
                return node

    def add(self, cursor: TokenOperator) -> Node:
        """
        add具象構文木

        add = mul("+" mul| "-" mul)*
        """
        node = self.mul(cursor)

        while 1:
            if cursor.consume("+"):
                node = self.create_new_node("+", NodeKind.ADD, node, self.mul(cursor))
            elif cursor.consume("-"):
                node = self.create_new_node("-", NodeKind.SUB, node, self.mul(cursor))
            else:
                return node

    def mul(self, cursor: TokenOperator) -> Node:
        """
        mul具象構文木

        mul = unary("*" unary | "/" unary)*
        """
        node = self.unary(cursor)

        while 1:
            if cursor.consume("*"):
                node = self.create_new_node("*", NodeKind.MUL, node, self.unary(cursor))
            elif cursor.consume("/"):
                node = self.create_new_node("/", NodeKind.DIV, node, self.unary(cursor))
            else:
                return node

    def unary(self, cursor: TokenOperator) -> Node:
        """
        unary具象構文木

        unary = ("+" | "-")? primary
        """
        if cursor.consume("+"):
            return self.primary(cursor)
        if cursor.consume("-"):
            return self.create_new_node(
                None,
                NodeKind.SUB,
                self.create_new_node(0, NodeKind.NUMBER, None, None),
                self.primary(cursor),
            )

        return self.primary(cursor)

    def primary(self, cursor: TokenOperator) -> Node:
        """
        primary具象構文木

        primary = num | identifier | "(" expression ")"
        """
        # (expr)
        if cursor.consume("("):
            node = self.expression(cursor)
            if cursor.consume(")") is False:
                raise ValueError("トークンのカッコが左右で対応していません")
            return node

        # identifier
        if cursor.chack_type(TokenKind.IDENTIFIER):
            value = cursor.get_value()
            cursor.proceed_cursor()

            new_node = self.create_new_local_var_node(value)
            return new_node

        if cursor.chack_type(TokenKind.NUMBER) is False:
            raise TypeError("数値型のトークンではありません")

        # num
        value = cursor.get_value()
        cursor.proceed_cursor()

        return self.create_new_node(value, NodeKind.NUMBER, None, None)
