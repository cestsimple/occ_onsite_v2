# -*- coding:utf-8 -*-
from typing import Any

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
    is_template: bool = False
    is_public: bool = False
    created_user: Any
    assigned_role: Any


class QuestionIn(Schema):
    questionnaire: Any
    content: str
    question_type: str
    order: int


class QuestionOut(Schema):
    questionnaire: QuestionnaireOut
    content: str
    question_type: str
    order: int
