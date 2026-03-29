# -*- coding: utf-8 -*-
from __future__ import annotations

import json
from pathlib import Path
from typing import TYPE_CHECKING

from chaoxing.models.sign import (
    SignActivity,
    SignCaptchaCheckResult,
    SignCaptchaData,
    SignContext,
    SignLocation,
    SignResultStatus,
    SignSubmitResult,
    SignType,
)

if TYPE_CHECKING:
    from chaoxing.core.base import Chaoxing


class BaseSigner:
    sign_type = SignType.UNKNOWN

    def __init__(self, client: "Chaoxing", context: SignContext):
        self.client = client
        self.context = context
        if self.context.sign_type == SignType.UNKNOWN:
            self.context.sign_type = self.sign_type

    @property
    def active_id(self) -> int:
        return self.context.active_id

    def get_detail(self):
        detail = self.client.get_sign_detail(self.active_id)
        self.context.sign_type = detail.sign_type
        return detail

    def pre_sign(self):
        return self.client.pre_sign(self.context)

    def get_captcha(self) -> SignCaptchaData:
        return self.client.get_sign_captcha(self.context)

    def check_captcha(self, x_position: float, captcha: SignCaptchaData) -> SignCaptchaCheckResult:
        return self.client.check_sign_captcha(self.context, x_position=x_position, captcha_data=captcha)

    def submit_auto(
        self,
        *,
        sign_code: str | int | None = None,
        enc: str | None = None,
        location: SignLocation | None = None,
        image_path: str | Path | None = None,
        object_id: str | None = None,
        validate: str | None = None,
        pre_sign: bool = True,
    ) -> SignSubmitResult:
        raise NotImplementedError

    def submit_with_captcha_auto(
        self,
        *,
        x_position: float,
        captcha_data: SignCaptchaData | None = None,
        sign_code: str | int | None = None,
        enc: str | None = None,
        location: SignLocation | None = None,
        image_path: str | Path | None = None,
        object_id: str | None = None,
        pre_sign: bool = True,
    ) -> SignSubmitResult:
        challenge = captcha_data or self.get_captcha()
        captcha_result = self.check_captcha(x_position, challenge)
        if not captcha_result.success or not captcha_result.validate_token:
            raw_message = captcha_result.message or "验证码校验失败"
            raw_payload = ""
            if captcha_result.raw:
                raw_payload = json.dumps(captcha_result.raw, ensure_ascii=False, separators=(",", ":"))
            return SignSubmitResult(
                active_id=self.active_id,
                sign_type=self.context.sign_type,
                status=SignResultStatus.CAPTCHA_REQUIRED,
                message=raw_message,
                raw_response=raw_payload,
                captcha_required=True,
            )
        return self.submit_auto(
            sign_code=sign_code,
            enc=enc,
            location=location,
            image_path=image_path,
            object_id=object_id,
            validate=captcha_result.validate_token,
            pre_sign=pre_sign,
        )


class NormalSigner(BaseSigner):
    sign_type = SignType.NORMAL

    def submit_auto(
        self,
        *,
        sign_code: str | int | None = None,
        enc: str | None = None,
        location: SignLocation | None = None,
        image_path: str | Path | None = None,
        object_id: str | None = None,
        validate: str | None = None,
        pre_sign: bool = True,
    ) -> SignSubmitResult:
        return self.client._submit_sign(
            context=self.context,
            sign_type=self.sign_type,
            validate=validate,
            pre_sign=pre_sign,
        )


class SignCodeSigner(BaseSigner):
    sign_type = SignType.SIGNCODE

    def submit_auto(
        self,
        *,
        sign_code: str | int | None = None,
        enc: str | None = None,
        location: SignLocation | None = None,
        image_path: str | Path | None = None,
        object_id: str | None = None,
        validate: str | None = None,
        pre_sign: bool = True,
    ) -> SignSubmitResult:
        if sign_code is None:
            raise ValueError("签到码签到需要提供 sign_code")
        return self.client._submit_sign(
            context=self.context,
            sign_type=self.sign_type,
            extra_params={"latitude": "", "longitude": "", "signCode": str(sign_code)},
            validate=validate,
            pre_sign=pre_sign,
        )


class GestureSigner(BaseSigner):
    sign_type = SignType.GESTURE

    def submit_auto(
        self,
        *,
        sign_code: str | int | None = None,
        enc: str | None = None,
        location: SignLocation | None = None,
        image_path: str | Path | None = None,
        object_id: str | None = None,
        validate: str | None = None,
        pre_sign: bool = True,
    ) -> SignSubmitResult:
        if sign_code is None:
            raise ValueError("手势签到需要提供 sign_code")
        return self.client._submit_sign(
            context=self.context,
            sign_type=self.sign_type,
            extra_params={"latitude": "", "longitude": "", "signCode": str(sign_code)},
            validate=validate,
            pre_sign=pre_sign,
        )


class LocationSigner(BaseSigner):
    sign_type = SignType.LOCATION

    def submit_auto(
        self,
        *,
        sign_code: str | int | None = None,
        enc: str | None = None,
        location: SignLocation | None = None,
        image_path: str | Path | None = None,
        object_id: str | None = None,
        validate: str | None = None,
        pre_sign: bool = True,
    ) -> SignSubmitResult:
        if location is None:
            raise ValueError("位置签到需要提供 location")
        return self.client._submit_sign(
            context=self.context,
            sign_type=self.sign_type,
            extra_params={
                "latitude": str(location.latitude),
                "longitude": str(location.longitude),
                "address": location.address,
            },
            validate=validate,
            pre_sign=pre_sign,
        )


class QRCodeSigner(BaseSigner):
    sign_type = SignType.QRCODE

    def submit_auto(
        self,
        *,
        sign_code: str | int | None = None,
        enc: str | None = None,
        location: SignLocation | None = None,
        image_path: str | Path | None = None,
        object_id: str | None = None,
        validate: str | None = None,
        pre_sign: bool = True,
    ) -> SignSubmitResult:
        if not enc:
            raise ValueError("二维码签到需要提供 enc")
        extra_params: dict[str, str] = {
            "enc": enc,
            "latitude": "-1",
            "longitude": "-1",
        }
        if location is not None:
            extra_params["location"] = json.dumps(
                {
                    "result": 1,
                    "latitude": f"{location.latitude:.6f}",
                    "longitude": f"{location.longitude:.6f}",
                    "address": location.address,
                    "mockData": "{\"strategy\":0,\"probability\":-1}",
                },
                ensure_ascii=False,
                separators=(",", ":"),
            )
        return self.client._submit_sign(
            context=self.context,
            sign_type=self.sign_type,
            extra_params=extra_params,
            validate=validate,
            pre_sign=pre_sign,
        )


class PhotoSigner(BaseSigner):
    sign_type = SignType.PHOTO

    def submit_auto(
        self,
        *,
        sign_code: str | int | None = None,
        enc: str | None = None,
        location: SignLocation | None = None,
        image_path: str | Path | None = None,
        object_id: str | None = None,
        validate: str | None = None,
        pre_sign: bool = True,
    ) -> SignSubmitResult:
        resolved_object_id = object_id
        if resolved_object_id is None and image_path is not None:
            resolved_object_id = self.client.upload_sign_photo(image_path).object_id
        extra_params: dict[str, str] = {}
        if resolved_object_id:
            extra_params["objectId"] = resolved_object_id
        return self.client._submit_sign(
            context=self.context,
            sign_type=self.sign_type,
            extra_params=extra_params,
            validate=validate,
            pre_sign=pre_sign,
        )


SIGNER_CLASS_MAP = {
    SignType.NORMAL: NormalSigner,
    SignType.PHOTO: PhotoSigner,
    SignType.QRCODE: QRCodeSigner,
    SignType.LOCATION: LocationSigner,
    SignType.GESTURE: GestureSigner,
    SignType.SIGNCODE: SignCodeSigner,
}


def create_signer(
    client: "Chaoxing",
    activity: SignActivity | SignContext | int,
    *,
    course_id: int | None = None,
    class_id: int | None = None,
    ext: str | None = None,
    sign_type: SignType | None = None,
) -> BaseSigner:
    context = client._resolve_sign_context(activity, course_id=course_id, class_id=class_id, ext=ext)
    if sign_type is not None:
        context.sign_type = sign_type
    if context.sign_type == SignType.UNKNOWN:
        context.sign_type = client.get_sign_detail(context.active_id).sign_type
    signer_cls = SIGNER_CLASS_MAP.get(context.sign_type, NormalSigner)
    return signer_cls(client, context)
