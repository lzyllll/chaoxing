# -*- coding: utf-8 -*-
from __future__ import annotations

import base64
import hashlib
import io
import json
import mimetypes
import re
import time
import uuid
from pathlib import Path
from typing import TYPE_CHECKING, Any

from loguru import logger

from chaoxing.core.config import GlobalConst as gc
from chaoxing.models.sign import (
    SignActivity,
    SignActivityPage,
    SignCaptchaCheckResult,
    SignCaptchaData,
    SignContext,
    SignDetail,
    SignLocation,
    SignPhotoUpload,
    SignPreflight,
    SignResultStatus,
    SignSubmitResult,
    SignType,
    SignUserProfile,
)

if TYPE_CHECKING:
    from chaoxing.core.base import Chaoxing


class SignMixin:
    MOBILE_USER_AGENT = (
        "Dalvik/2.1.0 (Linux; U; Android 12; SM-N9006 Build/8aba9e4.0) "
        "(schild:ce31140dfcdc2fcd113ccdd86f89a9aa) (device:SM-N9006) "
        "Language/zh_CN com.chaoxing.mobile/ChaoXingStudy_3_6.5.1_android_phone_10837_265 "
        "(@Kalimdor)_68f184fd763546c1a04ab3a09b3deebb"
    )
    SIGN_ACTIVITY_URL = "https://mobilelearn.chaoxing.com/v2/apis/active/student/activelist"
    SIGN_INFO_URL = "https://mobilelearn.chaoxing.com/v2/apis/active/getPPTActiveInfo"
    PRE_SIGN_URL = "https://mobilelearn.chaoxing.com/newsign/preSign"
    ANALYSIS_URL = "https://mobilelearn.chaoxing.com/pptSign/analysis"
    ANALYSIS2_URL = "https://mobilelearn.chaoxing.com/pptSign/analysis2"
    SIGN_URL = "https://mobilelearn.chaoxing.com/pptSign/stuSignajax"
    CHECK_SIGN_CODE_URL = "https://mobilelearn.chaoxing.com/widget/sign/pcStuSignController/checkSignCode"
    CAPTCHA_CONF_URL = "https://captcha.chaoxing.com/captcha/get/conf"
    CAPTCHA_IMAGE_URL = "https://captcha.chaoxing.com/captcha/get/verification/image"
    CAPTCHA_RESULT_URL = "https://captcha.chaoxing.com/captcha/check/verification/result"
    USER_INFO_URL = "https://sso.chaoxing.com/apis/login/userLogin4Uname.do"
    CLOUD_TOKEN_URL = "https://pan-yz.chaoxing.com/api/token/uservalid"
    CLOUD_UPLOAD_URL = "https://pan-yz.chaoxing.com/upload"
    SIGN_CAPTCHA_ID = "Qt9FIw9o4pwRjOyqM6yizZBh682qN2TU"
    SIGN_CAPTCHA_VERSION = "1.1.20"
    _ANALYSIS_CODE_RE = re.compile(r"code='\\+'([a-f0-9]+)'")
    _NO_SIGN_OFF_EVENT = {4999, -1}

    def _mobile_headers(self: "Chaoxing", referer: str | None = None) -> dict[str, str]:
        headers = dict(gc.HEADERS)
        headers["User-Agent"] = self.MOBILE_USER_AGENT
        if referer:
            headers["Referer"] = referer
        return headers

    def _get_or_create_device_code(self: "Chaoxing") -> str:
        device_code = getattr(self, "_sign_device_code", None)
        if device_code:
            return device_code
        raw_data = hashlib.sha256((uuid.uuid4().hex + uuid.uuid4().hex).encode()).digest()
        device_code = base64.b64encode(raw_data + raw_data).decode()
        setattr(self, "_sign_device_code", device_code)
        return device_code

    def _parse_jsonp_payload(self, payload: str) -> dict[str, Any]:
        text = payload.strip().rstrip(";")
        prefix = "cx_captcha_function("
        if text.startswith(prefix) and text.endswith(")"):
            text = text[len(prefix) : -1]
        return json.loads(text)

    def _sign_referer(self: "Chaoxing", context: SignContext) -> str:
        return (
            f"{self.PRE_SIGN_URL}?general=1&sys=1&ls=1&appType=15&isTeacherViewOpen=0"
            f"&courseId={context.course_id}"
            f"&classId={context.class_id}"
            f"&activePrimaryId={context.active_id}"
            f"&uid={self.get_uid()}"
        )

    def get_sign_user_profile(self: "Chaoxing", refresh: bool = False) -> SignUserProfile:
        cached = getattr(self, "_sign_user_profile", None)
        if cached is not None and not refresh:
            return cached

        response = self.session.get(self.USER_INFO_URL, headers=self._mobile_headers(), timeout=10)
        response.raise_for_status()
        payload = response.json().get("msg") or {}
        profile = SignUserProfile(
            uid=payload.get("uid"),
            puid=payload.get("puid", payload.get("uid")),
            fid=payload.get("fid"),
            name=payload.get("name") or "",
            school_name=payload.get("schoolname"),
            uname=payload.get("uname"),
            avatar_url=payload.get("pic"),
            raw=payload,
        )
        setattr(self, "_sign_user_profile", profile)
        return profile

    def list_sign_activities(self: "Chaoxing", course_id: int, class_id: int) -> SignActivityPage:
        response = self.session.get(
            self.SIGN_ACTIVITY_URL,
            params={
                "fid": 0,
                "showNotStartedActive": 0,
                "courseId": course_id,
                "classId": class_id,
            },
            headers=self._mobile_headers(),
            timeout=10,
        )
        response.raise_for_status()
        payload = response.json().get("data") or {}
        ext_payload = payload.get("ext")
        ext = json.dumps(ext_payload, ensure_ascii=False) if isinstance(ext_payload, dict) else str(ext_payload or "")
        activities = []
        for item in payload.get("activeList") or []:
            if item.get("type") not in (2, 74):
                continue
            sign_type = SignType.from_other_id(item.get("otherId"))
            activities.append(
                SignActivity(
                    active_id=int(item.get("id")),
                    course_id=int(course_id),
                    class_id=int(class_id),
                    ext=ext,
                    name=item.get("nameOne") or "",
                    end_name=item.get("nameFour") or "",
                    active_type=item.get("activeType"),
                    type=item.get("type"),
                    status=item.get("status"),
                    user_status=item.get("userStatus"),
                    other_id="" if item.get("otherId") is None else str(item.get("otherId")),
                    sign_type=sign_type,
                    is_look=item.get("isLook") == 1,
                    start_time=item.get("startTime"),
                    end_time=item.get("endTime"),
                    raw=item,
                )
            )
        return SignActivityPage(course_id=course_id, class_id=class_id, ext=ext, activities=activities)

    def get_sign_detail(self: "Chaoxing", active_id: int) -> SignDetail:
        response = self.session.get(
            self.SIGN_INFO_URL,
            params={"activeId": active_id},
            headers=self._mobile_headers(),
            timeout=10,
        )
        response.raise_for_status()
        payload = response.json().get("data") or {}
        sign_out_publish_time = payload.get("signOutPublishTimeStamp")
        if sign_out_publish_time in self._NO_SIGN_OFF_EVENT:
            sign_out_publish_time = None
        other_id = "" if payload.get("otherId") is None else str(payload.get("otherId"))
        return SignDetail(
            active_id=int(active_id),
            sign_type=SignType.from_other_id(other_id),
            name=payload.get("name") or "",
            title=payload.get("title"),
            other_id=other_id,
            status=payload.get("status"),
            user_status=payload.get("userStatus"),
            active_type=payload.get("activeType"),
            start_time=payload.get("starttime", payload.get("startTime")),
            end_time=payload.get("endTime"),
            late_end_time=payload.get("lateEndTime"),
            sign_in_id=payload.get("signInId"),
            sign_out_id=payload.get("signOutId"),
            sign_out_publish_time=sign_out_publish_time,
            number_count=payload.get("numberCount"),
            if_open_address=(payload.get("ifopenAddress") == 1) if "ifopenAddress" in payload else None,
            if_refresh_qrcode=(payload.get("ifrefreshewm") == 1) if "ifrefreshewm" in payload else None,
            if_need_vcode=(payload.get("ifNeedVCode") == 1) if "ifNeedVCode" in payload else None,
            location_latitude=payload.get("locationLatitude") or None,
            location_longitude=payload.get("locationLongitude") or None,
            location_range=payload.get("locationRange"),
            location_text=payload.get("locationText") or None,
            raw=payload,
        )

    def check_sign_code(self: "Chaoxing", active_id: int, sign_code: str | int) -> bool:
        response = self.session.get(
            self.CHECK_SIGN_CODE_URL,
            params={"activeId": active_id, "signCode": str(sign_code)},
            headers=self._mobile_headers(),
            timeout=10,
        )
        response.raise_for_status()
        return (response.json() or {}).get("result") == 1

    def create_signer(
        self: "Chaoxing",
        activity: SignActivity | SignContext | int,
        *,
        course_id: int | None = None,
        class_id: int | None = None,
        ext: str | None = None,
        sign_type: SignType | None = None,
    ):
        from chaoxing.signers import create_signer

        return create_signer(
            self,
            activity,
            course_id=course_id,
            class_id=class_id,
            ext=ext,
            sign_type=sign_type,
        )

    def pre_sign(
        self: "Chaoxing",
        activity: SignActivity | SignContext | int,
        *,
        course_id: int | None = None,
        class_id: int | None = None,
        ext: str | None = None,
    ) -> SignPreflight:
        context = self._resolve_sign_context(activity, course_id=course_id, class_id=class_id, ext=ext)
        detail = self.get_sign_detail(context.active_id)
        context.sign_type = detail.sign_type
        response = self.session.post(
            self.PRE_SIGN_URL,
            params={
                "general": 1,
                "sys": 1,
                "ls": 1,
                "appType": 15,
                "isTeacherViewOpen": 0,
                "courseId": context.course_id,
                "classId": context.class_id,
                "activePrimaryId": context.active_id,
                "uid": self.get_uid(),
            },
            data={"ext": context.ext},
            headers=self._mobile_headers(),
            timeout=10,
            allow_redirects=False,
        )
        body = response.text
        if response.status_code == 302 or "校验失败，未查询到活动数据" in body:
            raise ValueError("签到活动不存在，或者当前用户不在该班级内")
        response.raise_for_status()
        analysis_code = self._post_sign_analysis(context.active_id)
        already_signed = self._is_already_signed(detail.sign_type, body)
        return SignPreflight(
            active_id=context.active_id,
            sign_type=detail.sign_type,
            already_signed=already_signed,
            analysis_code=analysis_code,
            raw_html=body,
            detail=detail,
        )

    def upload_sign_photo(self: "Chaoxing", image_path: str | Path) -> SignPhotoUpload:
        path = Path(image_path).expanduser().resolve()
        if not path.exists() or not path.is_file():
            raise FileNotFoundError(f"找不到签到图片: {path}")
        with path.open("rb") as file_obj:
            content_type = mimetypes.guess_type(path.name)[0] or "image/jpeg"
            return self._upload_sign_photo_stream(path.name, file_obj, content_type, file_path=str(path))

    def upload_sign_photo_bytes(
        self: "Chaoxing",
        filename: str,
        content: bytes,
        *,
        content_type: str | None = None,
    ) -> SignPhotoUpload:
        if not content:
            raise ValueError("图片内容不能为空")
        resolved_content_type = content_type or mimetypes.guess_type(filename)[0] or "image/jpeg"
        with io.BytesIO(content) as file_obj:
            return self._upload_sign_photo_stream(filename, file_obj, resolved_content_type, file_path=filename)

    def _upload_sign_photo_stream(
        self: "Chaoxing",
        filename: str,
        file_obj,
        content_type: str,
        *,
        file_path: str,
    ) -> SignPhotoUpload:
        token_response = self.session.get(self.CLOUD_TOKEN_URL, headers=self._mobile_headers(), timeout=10)
        token_response.raise_for_status()
        token = (token_response.json() or {}).get("_token")
        if not token:
            raise ValueError("未获取到图片上传 token")

        response = self.session.post(
            self.CLOUD_UPLOAD_URL,
            params={"_from": "mobilelearn", "_token": token},
            data={"puid": str(self.get_sign_user_profile().puid or self.get_uid())},
            files={"file": (filename, file_obj, content_type)},
            headers=self._mobile_headers(),
            timeout=30,
        )
        response.raise_for_status()
        object_id = (response.json() or {}).get("objectId")
        if not object_id:
            raise ValueError("图片上传成功，但未返回 objectId")
        return SignPhotoUpload(token=token, object_id=object_id, file_path=file_path)

    def get_sign_captcha_conf(
        self: "Chaoxing",
        activity: SignActivity | SignContext | int,
        *,
        course_id: int | None = None,
        class_id: int | None = None,
        ext: str | None = None,
        captcha_id: str | None = None,
    ) -> int:
        self._resolve_sign_context(activity, course_id=course_id, class_id=class_id, ext=ext)
        response = self.session.get(
            self.CAPTCHA_CONF_URL,
            params={
                "callback": "cx_captcha_function",
                "captchaId": captcha_id or self.SIGN_CAPTCHA_ID,
                "_": str(int(time.time() * 1000)),
            },
            headers=self._mobile_headers(),
            timeout=10,
        )
        response.raise_for_status()
        payload = self._parse_jsonp_payload(response.text)
        return int(payload["t"])

    def get_sign_captcha(
        self: "Chaoxing",
        activity: SignActivity | SignContext | int,
        *,
        course_id: int | None = None,
        class_id: int | None = None,
        ext: str | None = None,
        captcha_id: str | None = None,
    ) -> SignCaptchaData:
        context = self._resolve_sign_context(activity, course_id=course_id, class_id=class_id, ext=ext)
        current_captcha_id = captcha_id or self.SIGN_CAPTCHA_ID
        timestamp = self.get_sign_captcha_conf(context, captcha_id=current_captcha_id)
        captcha_type = "slide"
        now_ms = int(time.time() * 1000)
        captcha_key = hashlib.md5(f"{timestamp}{uuid.uuid4()}".encode("utf8")).hexdigest()
        iv = hashlib.md5(
            f"{current_captcha_id}{captcha_type}{now_ms}{uuid.uuid4()}".encode("utf8")
        ).hexdigest()
        token = (
            hashlib.md5(f"{timestamp}{current_captcha_id}{captcha_type}{captcha_key}".encode("utf8")).hexdigest()
            + f":{timestamp + 300000}"
        )
        response = self.session.get(
            self.CAPTCHA_IMAGE_URL,
            params={
                "callback": "cx_captcha_function",
                "captchaId": current_captcha_id,
                "type": captcha_type,
                "version": self.SIGN_CAPTCHA_VERSION,
                "captchaKey": captcha_key,
                "token": token,
                "referer": self._sign_referer(context),
                "iv": iv,
                "_": str(now_ms),
            },
            headers=self._mobile_headers(),
            timeout=10,
        )
        response.raise_for_status()
        payload = self._parse_jsonp_payload(response.text)
        image_data = payload.get("imageVerificationVo") or {}
        shade_image = image_data.get("shadeImage")
        cutout_image = image_data.get("cutoutImage")
        if not shade_image or not cutout_image:
            raise ValueError("未获取到签到验证码图片")
        return SignCaptchaData(
            captcha_id=current_captcha_id,
            type=captcha_type,
            version=self.SIGN_CAPTCHA_VERSION,
            token=payload["token"],
            captcha_key=captcha_key,
            iv=iv,
            shade_image=shade_image,
            cutout_image=cutout_image,
        )

    def check_sign_captcha(
        self: "Chaoxing",
        activity: SignActivity | SignContext | int,
        *,
        x_position: float,
        captcha_data: SignCaptchaData,
        course_id: int | None = None,
        class_id: int | None = None,
        ext: str | None = None,
    ) -> SignCaptchaCheckResult:
        context = self._resolve_sign_context(activity, course_id=course_id, class_id=class_id, ext=ext)
        response = self.session.get(
            self.CAPTCHA_RESULT_URL,
            params={
                "callback": "cx_captcha_function",
                "captchaId": captcha_data.captcha_id,
                "type": captcha_data.type,
                "token": captcha_data.token,
                "textClickArr": json.dumps([{"x": int(x_position)}], ensure_ascii=False, separators=(",", ":")),
                "coordinate": "[]",
                "runEnv": "10",
                "version": captcha_data.version,
                "t": "a",
                "iv": captcha_data.iv,
                "_": str(int(time.time() * 1000)),
            },
            headers=self._mobile_headers(referer=self._sign_referer(context)),
            timeout=10,
        )
        response.raise_for_status()
        payload = self._parse_jsonp_payload(response.text)
        if payload.get("error") == 1:
            return SignCaptchaCheckResult(
                success=False,
                message=str(payload.get("msg") or "验证码校验失败"),
                raw=payload,
            )
        validate_value: str | None = None
        if payload.get("result"):
            extra_data = payload.get("extraData")
            if isinstance(extra_data, str) and extra_data:
                extra_payload = json.loads(extra_data.replace('\\"', '"'))
                validate_value = extra_payload.get("validate")
        return SignCaptchaCheckResult(
            success=bool(payload.get("result")) and bool(validate_value),
            validate_token=validate_value,
            message=str(payload.get("msg") or ""),
            raw=payload,
        )

    def submit_normal_sign(
        self: "Chaoxing",
        activity: SignActivity | SignContext | int,
        *,
        course_id: int | None = None,
        class_id: int | None = None,
        ext: str | None = None,
        validate: str | None = None,
        pre_sign: bool = True,
    ) -> SignSubmitResult:
        signer = self.create_signer(
            activity,
            course_id=course_id,
            class_id=class_id,
            ext=ext,
            sign_type=SignType.NORMAL,
        )
        return signer.submit_auto(validate=validate, pre_sign=pre_sign)

    def submit_signcode_sign(
        self: "Chaoxing",
        activity: SignActivity | SignContext | int,
        sign_code: str | int,
        *,
        course_id: int | None = None,
        class_id: int | None = None,
        ext: str | None = None,
        validate: str | None = None,
        pre_sign: bool = True,
    ) -> SignSubmitResult:
        signer = self.create_signer(
            activity,
            course_id=course_id,
            class_id=class_id,
            ext=ext,
            sign_type=SignType.SIGNCODE,
        )
        return signer.submit_auto(sign_code=sign_code, validate=validate, pre_sign=pre_sign)

    def submit_gesture_sign(
        self: "Chaoxing",
        activity: SignActivity | SignContext | int,
        sign_code: str | int,
        *,
        course_id: int | None = None,
        class_id: int | None = None,
        ext: str | None = None,
        validate: str | None = None,
        pre_sign: bool = True,
    ) -> SignSubmitResult:
        signer = self.create_signer(
            activity,
            course_id=course_id,
            class_id=class_id,
            ext=ext,
            sign_type=SignType.GESTURE,
        )
        return signer.submit_auto(sign_code=sign_code, validate=validate, pre_sign=pre_sign)

    def submit_location_sign(
        self: "Chaoxing",
        activity: SignActivity | SignContext | int,
        location: SignLocation,
        *,
        course_id: int | None = None,
        class_id: int | None = None,
        ext: str | None = None,
        validate: str | None = None,
        pre_sign: bool = True,
    ) -> SignSubmitResult:
        signer = self.create_signer(
            activity,
            course_id=course_id,
            class_id=class_id,
            ext=ext,
            sign_type=SignType.LOCATION,
        )
        return signer.submit_auto(location=location, validate=validate, pre_sign=pre_sign)

    def submit_qrcode_sign(
        self: "Chaoxing",
        activity: SignActivity | SignContext | int,
        enc: str,
        *,
        location: SignLocation | None = None,
        course_id: int | None = None,
        class_id: int | None = None,
        ext: str | None = None,
        validate: str | None = None,
        pre_sign: bool = True,
    ) -> SignSubmitResult:
        signer = self.create_signer(
            activity,
            course_id=course_id,
            class_id=class_id,
            ext=ext,
            sign_type=SignType.QRCODE,
        )
        return signer.submit_auto(enc=enc, location=location, validate=validate, pre_sign=pre_sign)

    def submit_photo_sign(
        self: "Chaoxing",
        activity: SignActivity | SignContext | int,
        *,
        image_path: str | Path | None = None,
        object_id: str | None = None,
        course_id: int | None = None,
        class_id: int | None = None,
        ext: str | None = None,
        validate: str | None = None,
        pre_sign: bool = True,
    ) -> SignSubmitResult:
        signer = self.create_signer(
            activity,
            course_id=course_id,
            class_id=class_id,
            ext=ext,
            sign_type=SignType.PHOTO,
        )
        return signer.submit_auto(
            image_path=image_path,
            object_id=object_id,
            validate=validate,
            pre_sign=pre_sign,
        )

    def submit_sign(
        self: "Chaoxing",
        activity: SignActivity | SignContext | int,
        *,
        course_id: int | None = None,
        class_id: int | None = None,
        ext: str | None = None,
        sign_code: str | int | None = None,
        enc: str | None = None,
        location: SignLocation | None = None,
        image_path: str | Path | None = None,
        object_id: str | None = None,
        validate: str | None = None,
        pre_sign: bool = True,
    ) -> SignSubmitResult:
        signer = self.create_signer(activity, course_id=course_id, class_id=class_id, ext=ext)
        return signer.submit_auto(
            sign_code=sign_code,
            enc=enc,
            location=location,
            image_path=image_path,
            object_id=object_id,
            validate=validate,
            pre_sign=pre_sign,
        )

    def submit_sign_with_captcha(
        self: "Chaoxing",
        activity: SignActivity | SignContext | int,
        *,
        x_position: float,
        captcha_data: SignCaptchaData | None = None,
        course_id: int | None = None,
        class_id: int | None = None,
        ext: str | None = None,
        sign_code: str | int | None = None,
        enc: str | None = None,
        location: SignLocation | None = None,
        image_path: str | Path | None = None,
        object_id: str | None = None,
        pre_sign: bool = True,
    ) -> SignSubmitResult:
        signer = self.create_signer(activity, course_id=course_id, class_id=class_id, ext=ext)
        return signer.submit_with_captcha_auto(
            x_position=x_position,
            captcha_data=captcha_data,
            sign_code=sign_code,
            enc=enc,
            location=location,
            image_path=image_path,
            object_id=object_id,
            pre_sign=pre_sign,
        )

    def _resolve_sign_context(
        self: "Chaoxing",
        activity: SignActivity | SignContext | int,
        *,
        course_id: int | None = None,
        class_id: int | None = None,
        ext: str | None = None,
    ) -> SignContext:
        if isinstance(activity, SignActivity):
            context = activity.to_context()
        elif isinstance(activity, SignContext):
            context = activity.model_copy()
        else:
            if course_id is None or class_id is None:
                raise ValueError("直接传 active_id 时必须同时提供 course_id 和 class_id")
            context = SignContext(
                active_id=int(activity),
                course_id=int(course_id),
                class_id=int(class_id),
                ext=ext or "",
            )

        if ext is not None:
            context.ext = ext
        if course_id is not None:
            context.course_id = int(course_id)
        if class_id is not None:
            context.class_id = int(class_id)

        if (not context.ext or context.sign_type == SignType.UNKNOWN) and context.course_id and context.class_id:
            try:
                page = self.list_sign_activities(context.course_id, context.class_id)
                matched = next((item for item in page.activities if item.active_id == context.active_id), None)
                if matched is not None:
                    context.ext = matched.ext or context.ext
                    context.sign_type = matched.sign_type
                    context.name = matched.name or context.name
            except Exception as exc:
                logger.debug("加载签到活动上下文失败: {}", exc)

        return context

    def _post_sign_analysis(self: "Chaoxing", active_id: int) -> str | None:
        response = self.session.get(
            self.ANALYSIS_URL,
            params={"vs": 1, "DB_STRATEGY": "RANDOM", "aid": active_id},
            headers=self._mobile_headers(),
            timeout=10,
        )
        response.raise_for_status()
        matched = self._ANALYSIS_CODE_RE.search(response.text)
        if matched is None:
            return None
        code = matched.group(1)
        analysis2 = self.session.get(
            self.ANALYSIS2_URL,
            params={"DB_STRATEGY": "RANDOM", "code": code},
            headers=self._mobile_headers(),
            timeout=10,
        )
        analysis2.raise_for_status()
        return code

    def _submit_sign(
        self: "Chaoxing",
        *,
        context: SignContext,
        sign_type: SignType,
        extra_params: dict[str, str] | None = None,
        validate: str | None = None,
        pre_sign: bool = True,
    ) -> SignSubmitResult:
        if pre_sign:
            preflight = self.pre_sign(context)
            if preflight.already_signed:
                return SignSubmitResult(
                    active_id=context.active_id,
                    sign_type=sign_type,
                    status=SignResultStatus.ALREADY_SIGNED,
                    message="已经签到过了",
                    raw_response=preflight.raw_html,
                    already_signed=True,
                )
        profile = self.get_sign_user_profile()
        params = {
            "activeId": str(context.active_id),
            "uid": str(profile.puid or profile.uid or self.get_uid()),
            "name": profile.name or self.account.username if self.account else "",
            "fid": str(profile.fid or self.get_fid() or 0),
            "deviceCode": self._get_or_create_device_code(),
        }
        if extra_params:
            params.update(extra_params)
        if validate:
            params["validate"] = validate

        response = self.session.get(
            self.SIGN_URL,
            params={
                "clientip": "",
                "appType": 15,
                "ifTiJiao": 1,
                "vpProbability": -1,
                "vpStrategy": "",
                **params,
            },
            headers=self._mobile_headers(),
            timeout=10,
        )
        response.raise_for_status()
        return self._parse_sign_response(context.active_id, sign_type, response.text)

    def _parse_sign_response(self, active_id: int, sign_type: SignType, response_text: str) -> SignSubmitResult:
        raw_text = response_text.strip()
        if raw_text == "success":
            return SignSubmitResult(
                active_id=active_id,
                sign_type=sign_type,
                status=SignResultStatus.SUCCESS,
                message="签到成功",
                raw_response=raw_text,
            )
        if raw_text.startswith("validate") or raw_text == "validate":
            return SignSubmitResult(
                active_id=active_id,
                sign_type=sign_type,
                status=SignResultStatus.CAPTCHA_REQUIRED,
                message="签到需要验证码",
                raw_response=raw_text,
                captcha_required=True,
            )
        if raw_text == "您已签到过了":
            return SignSubmitResult(
                active_id=active_id,
                sign_type=sign_type,
                status=SignResultStatus.ALREADY_SIGNED,
                message="已经签到过了",
                raw_response=raw_text,
                already_signed=True,
            )
        if raw_text == "success2":
            return SignSubmitResult(
                active_id=active_id,
                sign_type=sign_type,
                status=SignResultStatus.ENDED,
                message="迟到或签到已结束",
                raw_response=raw_text,
                ended=True,
            )
        if raw_text == "errorLocation2":
            return SignSubmitResult(
                active_id=active_id,
                sign_type=sign_type,
                status=SignResultStatus.WRONG_LOCATION,
                message="位置不在签到范围内",
                raw_response=raw_text,
                wrong_location=True,
            )
        return SignSubmitResult(
            active_id=active_id,
            sign_type=sign_type,
            status=SignResultStatus.ERROR,
            message=raw_text or "签到失败",
            raw_response=raw_text,
        )

    def _is_already_signed(self, sign_type: SignType, html: str) -> bool:
        if sign_type == SignType.PHOTO:
            return "请先拍照" not in html and '<div class="zactives-btn" onclick="send()">' not in html
        if sign_type == SignType.QRCODE:
            return "扫一扫" not in html
        if sign_type == SignType.LOCATION:
            return "恭喜你已完成签" not in html
        if sign_type == SignType.GESTURE:
            return "传达的手势图案" not in html
        if sign_type == SignType.SIGNCODE:
            return "输入发起者设置的签到码完成签到" not in html
        return "已签到" in html or "签到成功" in html
