# -*- coding: utf-8 -*-
from __future__ import annotations

from fastapi import APIRouter, File, Form, HTTPException, UploadFile
from pydantic import ValidationError
from sqlmodel import SQLModel

from chaoxing.models import SignLocation
from chaoxing.web.services.runtime import task_runtime_service

router = APIRouter(tags=["signs"])


class SignContextRequest(SQLModel):
    activeId: int
    courseId: int
    classId: int
    ext: str = ""
    signType: str | None = None


class SignLocationRequest(SQLModel):
    latitude: float
    longitude: float
    address: str


class SignSubmitRequest(SignContextRequest):
    signCode: str | None = None
    enc: str | None = None
    location: SignLocationRequest | None = None
    objectId: str | None = None
    preSign: bool = True


class SignCaptchaVerifyRequest(SignSubmitRequest):
    xPosition: float
    captchaData: dict


class SignCaptchaRecognizeRequest(SQLModel):
    captchaData: dict


def _to_sign_location(location: SignLocationRequest | None) -> SignLocation | None:
    if location is None:
        return None
    return SignLocation(
        latitude=location.latitude,
        longitude=location.longitude,
        address=location.address,
    )


@router.get("/accounts/{account_id}/courses/{course_snapshot_id}/signs")
def list_course_signs(account_id: int, course_snapshot_id: int) -> dict:
    try:
        return task_runtime_service.list_course_signs(account_id, course_snapshot_id)
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/accounts/{account_id}/signs/inspect")
def inspect_sign(account_id: int, payload: SignContextRequest) -> dict:
    try:
        return task_runtime_service.inspect_sign(
            account_id,
            active_id=payload.activeId,
            course_id=payload.courseId,
            class_id=payload.classId,
            ext=payload.ext,
            sign_type=payload.signType,
        )
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/accounts/{account_id}/signs/captcha")
def get_sign_captcha(account_id: int, payload: SignContextRequest) -> dict:
    try:
        return task_runtime_service.get_sign_captcha(
            account_id,
            active_id=payload.activeId,
            course_id=payload.courseId,
            class_id=payload.classId,
            ext=payload.ext,
            sign_type=payload.signType,
        )
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/accounts/{account_id}/signs/captcha/recognize")
def recognize_sign_captcha(account_id: int, payload: SignCaptchaRecognizeRequest) -> dict:
    try:
        return task_runtime_service.recognize_sign_captcha(
            account_id,
            captcha_data=payload.captchaData,
        )
    except ValidationError as exc:
        raise HTTPException(status_code=400, detail=exc.errors()) from exc
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/accounts/{account_id}/signs/submit")
def submit_sign(account_id: int, payload: SignSubmitRequest) -> dict:
    try:
        return task_runtime_service.submit_sign(
            account_id,
            active_id=payload.activeId,
            course_id=payload.courseId,
            class_id=payload.classId,
            ext=payload.ext,
            sign_type=payload.signType,
            sign_code=payload.signCode,
            enc=payload.enc,
            location=_to_sign_location(payload.location),
            object_id=payload.objectId,
            pre_sign=payload.preSign,
        )
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/accounts/{account_id}/signs/submit-with-captcha")
def submit_sign_with_captcha(account_id: int, payload: SignCaptchaVerifyRequest) -> dict:
    try:
        return task_runtime_service.submit_sign_with_captcha(
            account_id,
            active_id=payload.activeId,
            course_id=payload.courseId,
            class_id=payload.classId,
            ext=payload.ext,
            sign_type=payload.signType,
            x_position=payload.xPosition,
            captcha_data=payload.captchaData,
            sign_code=payload.signCode,
            enc=payload.enc,
            location=_to_sign_location(payload.location),
            object_id=payload.objectId,
            pre_sign=payload.preSign,
        )
    except ValidationError as exc:
        raise HTTPException(status_code=400, detail=exc.errors()) from exc
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/accounts/{account_id}/signs/photo/upload")
async def upload_sign_photo(
    account_id: int,
    file: UploadFile = File(...),
    content_type: str | None = Form(default=None),
) -> dict:
    filename = file.filename or "sign-photo.jpg"
    try:
        content = await file.read()
        return task_runtime_service.upload_sign_photo(account_id, filename, content, content_type or file.content_type)
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
