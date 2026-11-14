[app]
title = ReVols ER
package.name = revolser
package.domain = org.revols
source.dir = .
source.include_exts = py,png,jpg,kv,atlas,json
version = 1.0
requirements = python3,kivy==2.3.0,pyjnius
orientation = portrait
fullscreen = 0

android.permissions = INTERNET,ACCESS_NETWORK_STATE
android.archs = arm64-v8a
android.api = 33
android.minapi = 24
android.accept_sdk_license = True

[buildozer]
log_level = 2
warn_on_root = 1
