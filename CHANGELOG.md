# RoboBanana Changelog
## 2024.04.06
### Additions and Fixes:
- Added "Mod Role (Hidden)" to allowed roles for mod commands ([#142](https://github.com/crscillitoe/RoboBanana/pull/142)) (By [Leshy](https://github.com/lorinvzyl))
- Add Wildcard marker type, increase lockout to 180 seconds, create markers with a minute offset so they are in the past ([4058e0](https://github.com/crscillitoe/RoboBanana/commit/4058e035f771f9b8dd3d43ed42bef24dd0a10a48), [6f3ac3c](https://github.com/crscillitoe/RoboBanana/commit/6f3ac3c5e43d13e20a74054076ba9780a3f1c333))
- Add auditing for /manager redeem command ([#143](https://github.com/crscillitoe/RoboBanana/pull/143)) (By [Leshy](https://github.com/lorinvzyl))
- Add what command was used in audit logs ([#143](https://github.com/crscillitoe/RoboBanana/pull/143)) (By [Leshy](https://github.com/lorinvzyl))
- Change audit log user mentions to name + ID of user affected by command ([#143](https://github.com/crscillitoe/RoboBanana/pull/143)) (By [Leshy](https://github.com/lorinvzyl))
- Change structure of audit logs to look better ([#143](https://github.com/crscillitoe/RoboBanana/pull/143)) (By [Leshy](https://github.com/lorinvzyl))
## 2024.04.05
This update requires `/sync sync` to be run once
### Additions and Fixes:
- Added error handling to all slash domains (previously only t3, mod and manager had it) ([#139](https://github.com/crscillitoe/RoboBanana/pull/139))
- Added auditing of streamdeck prediction endpoints ([#140](https://github.com/crscillitoe/RoboBanana/pull/140))
- Added marker commands to easily allow multiple people to create stream markers for editors and VOD channel ([#141](https://github.com/crscillitoe/RoboBanana/pull/141))

## 2024.04.04
This update requires `/sync sync` to be run once
### Additions and Fixes:
- Added display of odds to prediction payout message ([a151b75](https://github.com/crscillitoe/RoboBanana/commit/a151b753cac61c3c4a152c24105e4bfc2cdab2bb))
- Added funcitonality for CMs to assign temproles, with a limit on which roles are allowed to be set with temproles in general ([#137](https://github.com/crscillitoe/RoboBanana/pull/137)) (By [Leshy](https://github.com/lorinvzyl))
- Added `sync info` command to display bot uptime and commit hash (Mod, CM, Trustworthy only) ([#138](https://github.com/crscillitoe/RoboBanana/pull/138))

## 2024.04.03
This update requires `/sync sync` to be run once
### Additions and Fixes:
- Added command to temporarily disable T3 TTS command (stays disabled until bot restart or enable command, mod only) (https://github.com/crscillitoe/RoboBanana/pull/129)
- Added command to temporarily set the price of the T3 TTS command (resets to 10k on bot restart, mod only) (https://github.com/crscillitoe/RoboBanana/pull/130)
- Fixed the bot timing out instead of responding to `/hooj bet` (https://github.com/crscillitoe/RoboBanana/pull/134) (By [Leshy](https://github.com/lorinvzyl))
- Fixed prediction buttons not allowing users to bet multiple times (now in line with command) (https://github.com/crscillitoe/RoboBanana/pull/136) (By [Leshy](https://github.com/lorinvzyl))

### Removals:
- `/hooj submit_vod` is now temporarily disabled. Tells users that VOD Reviews are on pause until Hooj hits Radiant. (https://github.com/crscillitoe/RoboBanana/pull/132)

### Changes:
- Moved prediction commands into their own `prediction` domain. Clears space in the mod domain and allows for better slash command permission settings in Discord itself (https://github.com/crscillitoe/RoboBanana/pull/128)
- Now always posts predictions into the prediction channel (https://github.com/crscillitoe/RoboBanana/pull/124)
- Only apply Crowdmute if the user is not already timed out (https://github.com/crscillitoe/RoboBanana/pull/133)
