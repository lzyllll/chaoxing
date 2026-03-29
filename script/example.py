# -*- coding: utf-8 -*-
# import sys
# import os
# sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import json
import sys

from chaoxing.core.base import Account, Chaoxing
from chaoxing.models import SignLocation
from chaoxing.ocr.slider import get_slider_distance


USERNAME = ""
PASSWORD = ""
COOKIES_PATH = "cookies.txt"
USE_COOKIES_LOGIN = False

COURSE_ID = 262291259
CLASS_ID = 143828737


SIGN_CODE = ""
QRCODE_ENC = ""
PHOTO_PATH = ""
PHOTO_OBJECT_ID = ""
CAPTCHA_VALIDATE = ""
CAPTCHA_X_POSITION = None

LOCATION = SignLocation(
    latitude=113.615,
    longitude=10.895,
    address="",
)


def dump(title: str, data) -> None:
    print(f"\n===== {title} =====")
    if hasattr(data, "model_dump"):
        print(json.dumps(data.model_dump(mode="json"), ensure_ascii=False, indent=2))
        return
    print(json.dumps(data, ensure_ascii=False, indent=2))


def build_client() -> Chaoxing:
    client = Chaoxing(
        account=Account(USERNAME, PASSWORD),
        cookies_path=COOKIES_PATH,
    )
    login_state = client.login(login_with_cookies=USE_COOKIES_LOGIN)
    if not login_state.get("status"):
        raise RuntimeError(f"登录失败: {login_state.get('msg', 'unknown error')}")
    return client


def main() -> None:
    client = build_client()

    courses = client.get_course_list()
    dump(
        "courses",
        [
            {
                "courseId": item.get("courseId"),
                "classId": item.get("clazzId"),
                "title": item.get("title"),
            }
            for item in courses
        ],
    )

    activities = client.list_sign_activities(course_id=COURSE_ID, class_id=CLASS_ID)
    dump("activities", activities)
    ACTIVE_ID = activities.activities[0].active_id 



    # 工厂方法会先把活动转成具体 signer，再由 signer 发起签到
    signer = client.create_signer(
        ACTIVE_ID,
        course_id=COURSE_ID,
        class_id=CLASS_ID,
    )

    detail = signer.get_detail()
    dump("detail", detail)

    pre_sign = signer.pre_sign()
    dump("pre_sign", pre_sign)

    # 普通签到
    # result = signer.submit_auto()
    # dump("submit_normal_sign", result)

    # captcha = signer.get_captcha()
    # dump("captcha", captcha)
    # CAPTCHA_X_POSITION = get_slider_distance(
    #     background_url=captcha.shade_image,
    #     target_url=captcha.cutout_image,
    # )
    # dump("captcha_x_position", CAPTCHA_X_POSITION)
    # if CAPTCHA_X_POSITION is not None:
    #     result = signer.submit_with_captcha_auto(
    #         x_position=float(CAPTCHA_X_POSITION),
    #         sign_code=SIGN_CODE or None,
    #         enc=QRCODE_ENC or None,
    #         location=LOCATION if LOCATION.address else None,
    #         image_path=PHOTO_PATH or None,
    #         object_id=PHOTO_OBJECT_ID or None,
    #     )
    #     dump("submit_with_captcha", result)

    # 签到码签到
    # result = signer.submit_auto(sign_code=SIGN_CODE)
    # dump("submit_signcode_sign", result)

    # 手势签到
    # result = signer.submit_auto(sign_code=SIGN_CODE)
    # dump("submit_gesture_sign", result)

    # 位置签到
    result = signer.submit_auto(location=LOCATION)
    dump("submit_location_sign", result)

    # 二维码签到
    # result = signer.submit_auto(
    #     enc=QRCODE_ENC,
    #     location=LOCATION if LOCATION.address else None,
    # )
    # dump("submit_qrcode_sign", result)

    # 拍照签到
    # 方式1
    # upload = client.upload_sign_photo(PHOTO_PATH)
    # print(upload.object_id)

    # result = signer.submit_auto(object_id=upload.object_id)
    # 方式2
    # result = signer.submit_auto(image_path=PHOTO_PATH)
    # dump("submit_photo_sign", result)

    # 如果 result.captcha_required 为 True，可继续走验证码闭环
    # captcha = signer.get_captcha()
    # dump("captcha", captcha)
    # if CAPTCHA_X_POSITION is not None:
    #     result = signer.submit_with_captcha_auto(
    #         x_position=float(CAPTCHA_X_POSITION),
    #         sign_code=SIGN_CODE or None,
    #         enc=QRCODE_ENC or None,
    #         location=LOCATION if LOCATION.address else None,
    #         image_path=PHOTO_PATH or None,
    #         object_id=PHOTO_OBJECT_ID or None,
    #     )
    #     dump("submit_with_captcha", result)


if __name__ == "__main__":
    main()
