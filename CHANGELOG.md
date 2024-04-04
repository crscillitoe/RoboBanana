# RoboBanana Changelog
## 2024.03.04
This update requires `/sync sync` to be run once
### Additions and Fixes:
- Added command to temporarily disable T3 TTS command (stays disabled until bot restart or enable command, mod only) (https://github.com/crscillitoe/RoboBanana/pull/129)
- Added command to temporarily set the price of the T3 TTS command (resets to 10k on bot restart, mod only) (https://github.com/crscillitoe/RoboBanana/pull/130)
- Fixed the bot timing out instead of responding to `/hooj bet` (https://github.com/crscillitoe/RoboBanana/pull/134) (By [lorinvzyl](https://github.com/lorinvzyl))
- Fixed prediction buttons not allowing users to bet multiple times (now in line with command) (https://github.com/crscillitoe/RoboBanana/pull/136) (By [lorinvzyl](https://github.com/lorinvzyl))

### Removals:
- `/hooj submit_vod` is now temporarily disabled. Tells users that VOD Reviews are on pause until Hooj hits Radiant. (https://github.com/crscillitoe/RoboBanana/pull/132)

### Changes:
- Moved prediction commands into their own `prediction` domain. Clears space in the mod domain and allows for better slash command permission settings in Discord itself (https://github.com/crscillitoe/RoboBanana/pull/128)
- Now always posts predictions into the prediction channel (https://github.com/crscillitoe/RoboBanana/pull/124)
- Only apply Crowdmute if the user is not already timed out (https://github.com/crscillitoe/RoboBanana/pull/133)
