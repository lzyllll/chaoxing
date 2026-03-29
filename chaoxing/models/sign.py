# -*- coding: utf-8 -*-
from __future__ import annotations

from enum import StrEnum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class SignType(StrEnum):
    NORMAL = "normal"
    PHOTO = "photo"
    QRCODE = "qrcode"
    LOCATION = "location"
    GESTURE = "gesture"
    SIGNCODE = "signcode"
    UNKNOWN = "unknown"

    @classmethod
    def from_other_id(cls, other_id: Any) -> "SignType":
        normalized = "" if other_id is None else str(other_id).strip()
        mapping = {
            "0": cls.PHOTO,
            "2": cls.QRCODE,
            "3": cls.GESTURE,
            "4": cls.LOCATION,
            "5": cls.SIGNCODE,
            "": cls.NORMAL,
        }
        return mapping.get(normalized, cls.UNKNOWN)


class SignResultStatus(StrEnum):
    SUCCESS = "success"
    CAPTCHA_REQUIRED = "captcha_required"
    ALREADY_SIGNED = "already_signed"
    ENDED = "ended"
    WRONG_LOCATION = "wrong_location"
    ERROR = "error"


class SignUserProfile(BaseModel):
    model_config = ConfigDict(extra="allow")

    uid: int | None = None
    puid: int | None = None
    fid: int | None = None
    name: str = ""
    school_name: str | None = None
    uname: str | None = None
    avatar_url: str | None = None
    raw: dict[str, Any] = Field(default_factory=dict)


class SignContext(BaseModel):
    active_id: int
    course_id: int
    class_id: int
    ext: str = ""
    sign_type: SignType = SignType.UNKNOWN
    name: str = ""


class SignActivity(BaseModel):
    model_config = ConfigDict(extra="allow")

    active_id: int
    course_id: int
    class_id: int
    ext: str = ""
    name: str = ""
    end_name: str = ""
    active_type: int | None = None
    type: int | None = None
    status: int | None = None
    user_status: int | None = None
    other_id: str = ""
    sign_type: SignType = SignType.UNKNOWN
    is_look: bool = False
    start_time: int | None = None
    end_time: int | None = None
    raw: dict[str, Any] = Field(default_factory=dict)

    def to_context(self) -> SignContext:
        return SignContext(
            active_id=self.active_id,
            course_id=self.course_id,
            class_id=self.class_id,
            ext=self.ext,
            sign_type=self.sign_type,
            name=self.name,
        )


class SignActivityPage(BaseModel):
    course_id: int
    class_id: int
    ext: str = ""
    activities: list[SignActivity] = Field(default_factory=list)


class SignDetail(BaseModel):
    model_config = ConfigDict(extra="allow")

    active_id: int
    sign_type: SignType = SignType.UNKNOWN
    name: str = ""
    title: str | None = None
    other_id: str = ""
    status: int | None = None
    user_status: int | None = None
    active_type: int | None = None
    start_time: int | None = None
    end_time: int | None = None
    late_end_time: int | None = None
    sign_in_id: int | None = None
    sign_out_id: int | None = None
    sign_out_publish_time: int | None = None
    number_count: int | None = None
    if_open_address: bool | None = None
    if_refresh_qrcode: bool | None = None
    if_need_vcode: bool | None = None
    location_latitude: float | None = None
    location_longitude: float | None = None
    location_range: int | None = None
    location_text: str | None = None
    raw: dict[str, Any] = Field(default_factory=dict)


class SignPreflight(BaseModel):
    active_id: int
    sign_type: SignType = SignType.UNKNOWN
    already_signed: bool = False
    analysis_code: str | None = None
    raw_html: str = ""
    detail: SignDetail | None = None


class SignLocation(BaseModel):
    latitude: float
    longitude: float
    address: str


class SignPhotoUpload(BaseModel):
    token: str
    object_id: str
    file_path: str


class SignCaptchaData(BaseModel):
    captcha_id: str
    type: str = "slide"
    version: str = "1.1.20"
    token: str
    captcha_key: str
    iv: str
    shade_image: str
    cutout_image: str


class SignCaptchaCheckResult(BaseModel):
    success: bool = False
    validate_token: str | None = None
    message: str = ""
    raw: dict[str, Any] = Field(default_factory=dict)


class SignSubmitResult(BaseModel):
    active_id: int
    sign_type: SignType = SignType.UNKNOWN
    status: SignResultStatus
    message: str
    raw_response: str = ""
    captcha_required: bool = False
    already_signed: bool = False
    ended: bool = False
    wrong_location: bool = False

    @property
    def is_success(self) -> bool:
        return self.status == SignResultStatus.SUCCESS
