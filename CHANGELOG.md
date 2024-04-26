# RoboBanana Changelog
## 2024.04.26
This update requires `/sync sync` to be run once
### Additions and Fixes:
- Add pokemon commands to stop stream chat spam and allow for more intricate handling ([#148](https://github.com/crscillitoe/RoboBanana/pull/148)) (By [Street/RyanO-K](https://github.com/RyanO-K))
- Improve pokemon commands to properly pass messages to the overlay ([7726730...8bb20ca](https://github.com/crscillitoe/RoboBanana/compare/8b5c781...8bb20ca))
## 2024.04.25
### Additions and Fixes:
- Fix absence of prediction close message when prediction is closed via API ([8b5c781](github.com/crscillitoe/RoboBanana/commit/8b5c781827d5927793346c6b0ef5e1fb0f454bc1))
## 2024.04.24
### Additions and Fixes:
- Allow Mods and Staff Devs to use T3 TTS for free ([3e9b479](github.com/crscillitoe/RoboBanana/commit/3e9b47925356dc8c0c260fcc2f2555cf1ef0ff1f))
- Improve handling of custom emoji message length check ([717d372](github.com/crscillitoe/RoboBanana/commit/717d372d8afd8ad372537f4a697297d8e98c0fd4))
## 2024.04.23
This update requires `/sync sync` to be run once
### Additions and Fixes:
- Added get_active_chatters command to get a random selection of active chatters and optionally assign them a role ([#147](https://github.com/crscillitoe/RoboBanana/pull/147))
## 2024.04.17
### Additions and Fixes:
- Allow new Dealer role to fully manage predictions ([e587abf](https://github.com/crscillitoe/RoboBanana/commit/e587abfd233e9ba11837ab92f1013fdf47439eeb))
## 2024.04.12
This update requires `/sync sync` to be run once
### Additions and Fixes:
- Limit prediction titles to 24 characters as more break the overlay for now ([97171c5](https://github.com/crscillitoe/RoboBanana/commit/97171c5fc8d054c28431bebbfc6a969b05cc4d58))
## 2024.04.11
This update requires `/sync sync` to be run once
### Additions and Fixes:
- Fix enable_tts_redemption not showing in slash commands ([#146](https://github.com/crscillitoe/RoboBanana/pull/146))
- Removed good morning payout and reset as that is successfully automatic for some time now ([#146](https://github.com/crscillitoe/RoboBanana/pull/146))
- Allow Staff Developers to sync and info ([63e3f35](https://github.com/crscillitoe/RoboBanana/commit/63e3f35e84e8e43b6285bccd428c3216491fefab))
## 2024.04.10
### Additions and Fixes:
- Fix variable names for audit function ([#145](https://github.com/crscillitoe/RoboBanana/pull/142)) (By [Leshy](https://github.com/lorinvzyl))
- Remove user.mention from audit_failed_message variable to use name + ID instead ([#145](https://github.com/crscillitoe/RoboBanana/pull/142)) (By [Leshy](https://github.com/lorinvzyl))
## 2024.04.09
### Additions and Fixes:
- Allowed Staff Developers to payout etc. predictions, as per Zendikar (https://github.com/crscillitoe/RoboBanana/pull/144)
## 2024.04.07
### Additions and Fixes:
- Added more guards to stop double prediction opening ([bbe1815](https://github.com/crscillitoe/RoboBanana/commit/bbe1815bf1599a0c662658cdcbc417732055028b))
- Now re-fetching Marker Thread and Message because of object timeouts, making Markers not re-create threads for single streams without bot restarts ([e8a2454](https://github.com/crscillitoe/RoboBanana/commit/e8a24545c1fd7b75ae693eee78d07348a6f61105))
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
