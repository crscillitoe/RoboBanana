# RoboBanana Changelog
## 2024.03.04
### Additions and Fixes:
- Added command to temporarily disable T3 TTS command (stays disabled until bot restart or enable command) (#129)
- Added command to temporarily set the price of the T3 TTS command (resets to 10k on bot restart) (#130)
- Fixed the bot timing out instead of responding to `/hooj bet` (#134)
- Fixed prediction buttons not allowing users to bet multiple times (now in line with command) (#136)

### Removals:
- `/hooj submit_vod` is now temporarily disables. Tells users that VOD Reviews are on pause until Hooj hits Radiant. (#132)

### Changes:
- Moved prediction commands into their own `prediction` domain. Clears space in the mod domain and allows for better slash command permission settings in Discord itself.
- Now always posts predictions into the prediction channel (#124)
- Only apply Crowdmute if the user is not already timed out (#133)
