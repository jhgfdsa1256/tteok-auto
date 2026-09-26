[app]

# (str) Title of your application
title = Mafia42 Tteok Auto Play

# (str) Package name
package.name = mafia42tteok

# (str) Package domain (needed for android/ios packaging)
package.domain = org.mafia42.tteok

# (source.dir) Source directory (where the main.py is)
source.dir = .

# (source.include_exts) Source include extensions (let empty to include all the files)
source.include_exts = py,png,jpg,kv,atlas

# (version) Application versioning (method 1)
version = 1.0.0

# (string) Application versioning (method 2)
# version.regex = __version__ = ['"](.*)['"]
# version.filename = %(source.dir)s/main.py

# (list) Application requirements
# comma separated e.g. requirements = sqlite3,kivy
requirements = python3,kivy,opencv,numpy,pillow

# (str) Supported orientation (landscape, portrait or all)
orientation = portrait

# (bool) Indicate if the application should be fullscreen or not
fullscreen = 0

# (string) Presplash of the application
# presplash.filename = %(source.dir)s/data/presplash.png

# (string) Icon of the application
# icon.filename = %(source.dir)s/data/icon.png

# (str) Permissions
android.permissions = INTERNET,CAMERA,WRITE_EXTERNAL_STORAGE,READ_EXTERNAL_STORAGE,BIND_ACCESSIBILITY_SERVICE

# (int) Target Android API, should be as high as possible.
android.api = 31

# (int) Minimum API your APK will support.
android.minapi = 21

# (int) Android SDK version to use
android.sdk = 31

# (str) Android NDK version to use
android.ndk = 25b

# (bool) Use --private data storage (True) or --dir public storage (False)
android.private_storage = True

# (str) Android app theme, default is ok for Kivy-based app
# In case of Kivy-based project, this is the name of the color
# scheme xml file for your app.
android.theme = "@android:style/Theme.NoTitleBar"

# (bool) Copy library instead of making a libpymodules.so
android.copy_libs = 1

# (str) The Android arch to build for, choices: armeabi-v7a, arm64-v8a, x86, x86_64
android.archs = arm64-v8a

# (bool) Enable AndroidX support
android.enable_androidx = True

# (list) Android application meta-data (name = value)
# android.meta_data = com.google.android.gms.version=@integer/google_play_services_version

# (str) Filename of OUYA Console icon. It must be a 732x412 png image.
# android.ouya.icon.filename = %(source.dir)s/data/ouya_icon.png

# (str) XML file for custom backup agent declaration within the manifest. See:
# https://developer.android.com/guide/topics/data/backup/backupagent
# android.backup_agent = mybackupagent.MyBackupAgent

# (str) XML file for custom backup agent declaration within the manifest. See:
# https://developer.android.com/guide/topics/data/backup/autobackup
# android.gradle_dependencies =

# (list) Pattern to whitelist for the whole project
#android.whitelist = lib-dynload/termios.so

# (bool) Copy library instead of making a libpymodules.so
# android.copy_libs = 1

# (str) The Android logcat filename, for android debugging
android.logcat_filename = /sdcard/Download/kivy.log

# (bool) Copy on each build the whole res directory from the source
android.copy_libs_src = 0

# (str) Gradle dependencies
android.gradle_dependencies = 

# (list) Java classes to add as services to the manifest.
android.services = org.kivy.android.PythonService

# (bool) Treat the android.gradle_dependencies as direct dependencies to the
# .gradle file. Don't set to 1 unless you know what you're doing!
# android.add_src = False

# (list) Pattern to whitelist for the whole project
#android.whitelist = lib-dynload/termios.so

# (bool) Copy library instead of making a libpymodules.so
# android.copy_libs = 1

# (str) The Android logcat filename, for android debugging
# android.logcat_filename = /sdcard/Download/kivy.log

# (bool) Copy on each build the whole res directory from the source
# android.copy_libs_src = 0

[buildozer]

# (int) Log level (0 = error only, 1 = info, 2 = debug (with command output))
log_level = 2

# (int) Display advance warning on buildozer run (used for function like android.gradle_dependencies)
# warn_on_root = 1

# (str) Path to build artifact storage, absolute or relative to spec file directory (./build)
#build_dir = ./.buildozer

# (str) Path to build output (i.e. .apk, .ipa) storage
# bin_dir = ./bin

# Log in to the buildozer user (if not allowed by default)
# buildozer.user = username

# Changed in 1.2.0 (new install page)
# If the buildozer user is different from the current user, it must be specified here
# buildozer.user = username
