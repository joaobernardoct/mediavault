# README

### What is this?
This script was designed to organize photos by (1) renaming them to their date and (2) generating a folder structure with yearly and monthly partitions. 

An example follows:
```
.
├── 2022
│   ├── 01
│   |    └── 2023.01.01 (12h40m15s).jpg
│   ├── 02
│   ├── ...   
│   └── 12
└── 2023
    └── ...
```

### Supported file types and extensions

| File type | Description | Extensions |
| --------- | ----------- | ---------- |
| Images | The capture date can be retrieved from images that follow the EXIF standard. | .jpg  .tiff  .gif  .bmp  .raw  .cr2  .nef  .orf  .arw  .rw2  .dng  .jpeg  .heic  .heif |
| Videos | The capture date can be retrieved from videos that (whilst not following a specific standard) include metadata in the format "%Y-%m-%d %H:%M:%S". | .mp4  .mov  .mkv  .avi  .flv  .webm  .m4v |

**Noteworthy:** When metadata is not present, the script parses the name of the image to understand if there is a date that can be used. However, it is important to note that the date extracted from this procedure might not be the actual capture date (e.g. A photo was taken on 2020 and sent to you on 2022. Your file system will store it as if it was from 2022). Mark the flag `SHOULD_PROCESS_NOT_EXIF = false` to avoid this.

### How to run

Run it:
```
# add the script inside of the photos folder
python3 MediaVault.py
```
* Please note that you can also revert the MediaVault operation, by running the `revertMediaVault.py` script inside of the `_MediaVault/` generated directory


Configure it:
| Macro | Description | Default |
| ----- | ----------- | ------- |
| IM_FEELING_LUCKY | If you're feeling lucky, the script will look for a capture date even if it is not on the file's metadata. Note that while this extends the script's capabilities, it is way more error prone. Use at your own risk. | False | 
| NR_IMAGES_PER_DAY | If the number of files belonging to a certain day is > NR_IMAGES_PER_DAY , they'll be placed on a folder for that day | 20 |
|WEE_SMALL_HOURS_OF_THE_MORNING | Sets the end of a day. e.g. photos at 04:00 usually relate to the end of the previous day and not the beggining of the next. Note that this does not change the date of the photo itself, it is only used when creating folders | "04.00.00" |
|MONTHLY_PARTITION| Whether we should create monthly partitions inside the yearly partition | True |
|TRAVERSE_SUBDIRS | Whether we should also traverse subdirs. It is safer to be turned off | False |
|DEBUG| Debug mode (increased verbosity) | False |

---
---
---
---
---
---
---
---
---
---
---

# Relevant Changelog
                                            
* `2019.09.21` - Renames WhatsApp images and videos from  "IMG-YYYYMMDD-WAXXXX" to "YYYY.MM.DD"

* `2020.10.10` - Add support for Samsung cellphone's Screenshots and Camera Roll

* `2022.02.10` - Refactored into classes for improved readibility and removing redundant code

* `2022.09.26` - Added safeguards to (i) avoid overwriting files (ii) ensure the exctracted capture dates are a valid date. Added toggleable support for organizing files of the same day into a common subfolder.

* `2023.07.08` - Updated the script's processing logic used to extract the capture date. It primarily relies on file's metadata rather than on filename (the latter is now a toggleable option in case the first did not succeed).

* `2023.10.18` - Renamed the script from "StoreArtifacts" to "MediaVault". Refactored the script from end-to-end, mainly: (i) the Organizer class ingests files `.ingest()` and updates a csv with their path, capture date and time (ii) the Organizer class organizes files `.organize()` by traversing the mentioned csv (iii) whether to ingest files from subfolders is now a toggleable option (iv) the script now keeps a record `log.md` of each rename to allow rolling back to previous state.

* `2024.01.22` - Added support for monthly organization in each yearly folder and fixed some small bugs

* `2024.01.26` - Update validations for valid time and date
