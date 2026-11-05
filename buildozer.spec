[app]
p4a.local_recipes = p4a-recipes
title = Lumen
package.name = lumen
package.domain = org.tanmay
source.dir = .
source.include_exts = py,png,wav,json
source.exclude_dirs = .venv,.git,.github,.buildozer,bin,docs,tests,__pycache__
version = 1.0
requirements = python3,kivy==2.3.1
orientation = portrait
fullscreen = 0
icon.filename = %(source.dir)s/assets/icon.png
presplash.filename = %(source.dir)s/assets/presplash.png
android.presplash_color = #080B1A
android.archs = arm64-v8a
android.accept_sdk_license = True

[buildozer]
log_level = 2
warn_on_root = 1
