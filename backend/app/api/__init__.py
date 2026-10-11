"""API 路由汇总。"""
from fastapi import APIRouter

from app.api import auth, contracts, reviews, reports, knowledge

api_router = APIRouter()
api_router.include_router(auth.router)
api_router.include_router(contracts.router)
api_router.include_router(reviews.router)
api_router.include_router(reports.router)
api_router.include_router(knowledge.router)
