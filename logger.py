from datetime import datetime

class Logger:
    nowTime = datetime.now()
    audioVideoMerge = f'LOGGER: {nowTime} : MERGING AUDIO WITH VIDEO'
    savingMergedVideo = f'LOGGER: {nowTime} : SAVING MERGED VIDEO'
    toSRT = f'LOGGER: {nowTime} : CONVERTING TEXT TO SRT'
    subtitleCreate = f'LOGGER: {nowTime} : CREATING SUBTITLES'
    subtitleVieoMerge = f'LOGGER: {nowTime} : MERGING VIDEO WITH SUBTITLES'
    buildingVideo = f'Logger: {nowTime} : BUILDING VIDEO'
    writingVideo = f'Logger: {nowTime} : WRITING VIDEO'
    subVideoCreated = f'Logger: {nowTime} : SUBCLIP CREATED'
    mainVideoCreated = f'Logger: {nowTime} : COMPLETE VIDEO FINISHED'