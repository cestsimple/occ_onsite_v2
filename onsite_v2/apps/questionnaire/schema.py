# -*- coding:utf-8 -*-
from ninja import Schema


class QuestionnaireOut(Schema):
    id: int
    title: str
    is_template: int
    is_public: int
    created_user: str
    assigned_role: str
