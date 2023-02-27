# -*- coding:utf-8 -*-
from ninja import Schema


class UserOut(Schema):
    id: int
    username: str
    region: str


class RoleOut(Schema):
    id: int
    name: str


class QuestionnaireOut(Schema):
    id: int
    title: str
    is_template: int
    is_public: int
    created_user: UserOut
    assigned_role: RoleOut


class QuestionnaireIn(Schema):
    title: str
    is_template: bool
    is_public: bool
    created_user: str
    assigned_role: str
