import csv
import os
import re
import sys
import shutil
from datetime import datetime, timedelta      # utils date
from hachoir.parser import createParser       # utils video
from hachoir.metadata import extractMetadata  # utils video
from PIL import Image as PILImage             # utils image
from PIL.ExifTags import TAGS                 # utils image




##################################################################
#                        GENERAL SETTINGS                        #
##################################################################

# If you're feeling lucky, the script will look for a capture date even if it is not on
# the file's metadata. Note that while this extends the script's capabilities, it is way
# more error prone. Use at your own risk.
IM_FEELING_LUCKY = True

# Organize into folders properties:
# (i) If the number of files belonging to a certain day is > NR_IMAGES_PER_DAY , they'll be
#     placed on a folder for that day
# (ii) Sets the end of a day
#      e.g. photos at 04:00 usually relate to the end of the previous day and not the beggining of the next
#      Note that this does not change the date of the photo itself, it is only used when creating folders
NR_IMAGES_PER_DAY = 20
WEE_SMALL_HOURS_OF_THE_MORNING = datetime.strptime("04.00.00", "%H.%M.%S")

# Whether we should also traverse subdirs. It is safer to be turned off
TRAVERSE_SUBDIRS = True



##################################################################
#                             MACROS                             #
##################################################################
EXIF_STANDARD_CREATION_DATE = 1998

DATE_FORMAT = "%Y.%m.%d"
DATE_FORMAT_REGEX = r"(\d{4}\.\d{2}\.\d{2})"
TIME_FORMAT = "%H.%M.%S"
TIME_FORMAT_REGEX = r"(\d{2}\.\d{2}\.\d{2})"
OUTPUT_FORMAT = "%Y.%m.%d (%Hh%Mm%Ss)" # This represents how the images will be renamed
OUTPUT_FORMAT_REGEX = r"(\d{4}\.\d{2}\.\d{2}) \((\d{2}h\d{2}m\d{2}s)\)"




##################################################################
#                            MAIN                                #
##################################################################
class Main():
    def __init__(self):
        self.organizer = Organizer()

    def run(self):
        for root, dirs, files in os.walk('.'):
            for filename in sorted(files):
                file = os.path.join(root, filename)
                self.organizer.ingestFile(file)

            if not TRAVERSE_SUBDIRS:
                break

        self.organizer.organize()

        print("Success ;)")




########################################################################
#                               ORGANIZER                              #
#                                                                      #
# 1st: .ingestFile - Ingest a file and process it, i.e. store the      #
#                    file path, capture date and capture time on a csv #
# 2nd: .organize - Rename and organize photos into folders using the   #
#                  generated csv content                               #
########################################################################
class Organizer():

    def __init__(self):
        # instantiate necessary classes
        self.imageProcessor = ImageProcessor()
        self.videoProcessor = VideoProcessor()
        self.hero           = UnprocessedImageAndVideoProcessor()
        self.mediaVaultCsv  = MediaVaultCSV()

        # dateCounter --> tracks the number of images per date (to organize into folders)
        self.dateCounter = {}

        # processedFolder --> the abs path to the folder where processed images should be placed
        self.processedFolder = os.getcwd() + "/" + "_Media Vault" + "/"
        if not os.path.exists(self.processedFolder):
            os.makedirs(self.processedFolder, exist_ok=True)

        # logFile --> each rename/move operation will be logged here
        logFilePath = self.processedFolder + "_log.md"
        if not os.path.exists(logFilePath):
            self.logFile = open(logFilePath, "w", newline='') 
            self.logFile.write("| Old File Path | New File Path |\n")
            self.logFile.write("| ------------- | ------------- |\n") 
        else:
            self.logFile = open(logFilePath , "a", newline='')


    # The entrypoint for file processing
    def ingestFile(self, filename):
            # NOTE: captureDate expects a tuple  ("YYYY.MM.DD" , "HH.MM.SS")
            isImage   = self.imageProcessor.isImage(filename)
            isVideo   = self.videoProcessor.isVideo(filename)

            # If the file type is not supported, ignore the file
            if (not isVideo and not isImage):
                return

            # Process file (by metadata)
            if isImage:
                captureDate = self.imageProcessor.getImageCaptureDate(filename)
            elif isVideo:
                captureDate = self.videoProcessor.getVideoCaptureDate(filename)

            # Process file (without metadata)
            #   If the capture date was not retrieve using metadata and IM_FEELING_LUCKY is set to true,
            #   try to retrieve the capture date with other (more error prone) methodologies
            if captureDate[0] is None and IM_FEELING_LUCKY:
                captureDate = self.hero.getCaptureDateFromFilename(filename)

            date = captureDate[0]
            time = captureDate[1]
            filePath = os.path.abspath(filename)

            # Validate capture date - if it is not valid, ignore the file
            if not self.isValidCaptureDate(date, time):
                return

            # If the capture date is valid, store file information into csv
            fileDataToPersistOnCSV = {
                'OriginalPath': filePath,
                'CaptureDate': date,
                'CaptureTime': time,
                'NewPath' : ''
            }
            self.mediaVaultCsv.write(fileDataToPersistOnCSV)

            # Additionally, update the dateCounter
            dateToCount = self.weeSmallHoursOfTheMorning(date, time)
            self.dateCounter[dateToCount] = self.dateCounter.get(dateToCount, 0) + 1


    def isValidCaptureDate(self, date, time):
        if date is None:
            return False
        condition1 = int(date[:4]) >= EXIF_STANDARD_CREATION_DATE
        condition2 = re.match(DATE_FORMAT_REGEX, date) is not None
        condition3 = re.match(TIME_FORMAT_REGEX, time) is not None if time is not None else True
        return (condition1 and condition2 and condition3)


    def organize(self):
        
        # Setup the csv reader
        reader = self.mediaVaultCsv.read()
        try:
            # Skip the header row
            next(reader)
        except StopIteration:
            # If there is not a second row, there are no entries
            print ("No files were processed.")
            sys.exit(0)

        # Traverse csv to rename and organize each file
        for row in reader:
            oldFilePath = row[0]
            date = row[1]
            time = row[2]

            # Calculate relative date
            relativeDate = self.weeSmallHoursOfTheMorning(date, time)
            relativeYear = relativeDate[:4]

            # Calculate the new file location and create the necessary folder structure
            newFileLocation = self.processedFolder + relativeYear + "/"     # .../YYYY
            if self.dateCounter.get(relativeDate, 0) >= NR_IMAGES_PER_DAY:
                newFileLocation += relativeDate + "/"                       # .../YYYY/YYYY.MM.DD
            os.makedirs(newFileLocation, exist_ok=True)

            # Calculate the new file name
            fileExtension = os.path.splitext(oldFilePath)[1]
            newFileName = self.renameWithCaptureDate(newFileLocation, fileExtension, date, time)

            # Rename and move the file and log this changes
            os.rename(oldFilePath, newFileLocation + newFileName)
            self.logFile.write('|' + oldFilePath + '|' + newFileLocation + newFileName + '|\n')
        
        # After traversing, delete mediaVaultCsv
        self.mediaVaultCsv.delete()
        

    # Responsible for the logic of WEE_SMALL_HOURS_OF_THE_MORNING
    # Returns a date
    def weeSmallHoursOfTheMorning(self, date, time):
        # if time is not available, don't perform any computation, just return the date
        if not time:
            return date
        time_difference = abs( int( (datetime.strptime(time, "%H.%M.%S") - WEE_SMALL_HOURS_OF_THE_MORNING).days ) )
        date = str( (datetime.strptime(date, "%Y.%m.%d") - timedelta(days=time_difference)) ).replace("-",".")[:10]
        return date


    # Responsible for returning the new file name
    def renameWithCaptureDate(self, newFileLocation, fileExtension, date, time):
        # Calculate newFilename
        if time:
            newFilename = str(datetime.strptime(date + ' ' + time, DATE_FORMAT + ' ' + TIME_FORMAT).strftime(OUTPUT_FORMAT))
        else:
            newFilename = date

        # Find a unique filename (to ensure we avoid overriding on the newFileLocation)
        counter = 1
        newUniqueFilename = f"{newFilename}{fileExtension}"
        while (os.path.exists(newFileLocation + newUniqueFilename)):
            newUniqueFilename = f"{newFilename} ({counter}){fileExtension}"
            counter += 1

        return newUniqueFilename



##################################################################
#                         MEDIA VAULT CSV                        #
##################################################################
class MediaVaultCSV():

    def __init__(self):
        # csvFile --> a csv where ingest() will write and from which organize() will read afterwards
        self.csvFile = os.getcwd() + "/" + "mediaVaultData.csv"
        self.setup()        


    # Sets up the mediaVaultCsv on instantiation
    def setup(self):
        if os.path.exists(self.csvFile):
            print("ERROR: A mediaVaultData.csv already exists in the working directory. Will not override it.")
            sys.exit(1)  # Halt the program as it should not run with logging its changes

        try:
            headerCSV = {
                'OriginalPath': 'OriginalPath',
                'CaptureDate': 'CaptureDate',
                'CaptureTime': 'CaptureTime',
                'NewPath' : 'NewPath'
            }
            self.write(headerCSV)
        except Exception as e:
            print("ERROR: Was not able to create/write to data.csv. Halting.")
            print(e)
            sys.exit(1) # Halt


    # Writes a row to the mediaVaultData.csv provided a dictionary with the following fields:
    # 'OriginalPath' , 'CaptureDate' , 'CaptureTime' , 'NewPath' (the order needs to be followed!)
    def write(self, row):
        with open(self.csvFile, "a", newline='') as file:
            # Write the header to the CSV file
            csv.writer(file).writerow(row.values())
        file.close()


    # Returns a csv.reader
    def read(self):
        # Setup the csv reader
        try:
            file = open(self.csvFile, 'r')
            reader = csv.reader(file)
            if reader:
                return reader
            else:
                # If the CSV is empty, halt the program
                print("ERROR: CSV file is empty. Halting.")
                sys.exit(1)
        except Exception as e:
            print ("ERROR: " + e)
            sys.exit(1)


    def delete(self):
        if os.path.exists(self.csvFile):
            os.remove(self.csvFile)



##################################################################
#                         IMAGE PROCESSOR                        #
##################################################################
class ImageProcessor():

    def isImage(self, file_path):
        try:
            PILImage.open(file_path)
            return True
        except (IOError, SyntaxError):
            return False

    # Returns the capture date as a tuple ("YYYY.MM.DD" , "HH.MM.SS")
    def getImageCaptureDate(self, imagePath):
        try:
            image = PILImage.open(imagePath)
            for tag_id, value in image._getexif().items():
                if TAGS.get(tag_id, tag_id) == "DateTimeOriginal":
                    capture_date = str(value)

                    input_format = "%Y:%m:%d %H:%M:%S"
                    date = str(datetime.strptime(capture_date, input_format).strftime(DATE_FORMAT))
                    time = str(datetime.strptime(capture_date, input_format).strftime(TIME_FORMAT))
                    return (date, time)
        except Exception as e:
            pass
        return (None, None)




##################################################################
#                         VIDEO PROCESSOR                        #
##################################################################
class VideoProcessor():

    def isVideo(self, video_path):
        # We currently only support video formats that typically store capture dates in the format "%Y-%m-%d %H:%M:%S"
        video_extensions = ['.mp4', '.mov', '.mkv', '.avi', '.flv', '.webm', '.m4v']
        file_extension = os.path.splitext(video_path)[1].lower()
        return file_extension in video_extensions

    # Returns the capture date as a tuple ("YYYY.MM.DD" , "HH.MM.SS")
    def getVideoCaptureDate(self, video_path):
        try:
            capture_date = str(extractMetadata(createParser(video_path)).get('creation_date'))

            input_format = "%Y-%m-%d %H:%M:%S"
            date = str(datetime.strptime(capture_date, input_format).strftime(DATE_FORMAT))
            time = str(datetime.strptime(capture_date, input_format).strftime(TIME_FORMAT))
            return (date, time)
        except Exception as e:
            pass
        return (None, None)




##################################################################
#             UNPROCESSED IMAGE AND VIDEO PROCESSOR              #
##################################################################
class UnprocessedImageAndVideoProcessor():

    # Returns the capture date as a tuple ("YYYY.MM.DD" , "HH.MM.SS")
    # TODO expand cases
    def getCaptureDateFromFilename(self, imagePath):
        filename = os.path.basename(imagePath)

        searchPatternList = [ r'IMG_(\d{4})(\d{2})(\d{2})' , # Whatsapp image or video
                      r'WhatsApp Image (\d{4})-(\d{2})-(\d{2}) at (\d{2})\.(\d{2})\.(\d{2})' , # Whatsapp image (old)
                      r'WhatsApp Video (\d{4})-(\d{2})-(\d{2}) at (\d{2})\.(\d{2})\.(\d{2})' , # Whatsapp video (old)
                      r'Screenshot_(\d{4})(\d{2})(\d{2})-(\d{2})(\d{2})(\d{2})' , # Samsung phone screenshots
                      r'(\d{4})(\d{2})(\d{2})_(\d{2})(\d{2})(\d{2})' , # Samsung phone camera roll
                      r'(\d{4})\.(\d{2})\.(\d{2}) \((\d{2})h(\d{2})m(\d{2})s\)' # This script (so it is idempotent)
                    ]

        for pattern in searchPatternList:
            match = re.search(pattern, filename)
            if match:
                # if it matched a date
                if match.re.groups == 3:
                    year, month, day = match.groups()
                    date = year + "." + month + "." + day
                    return (date, None)
                # if it matched a date and a time
                elif match.re.groups == 6:
                    year, month, day, hour, minute, second = match.groups()
                    date = year + "." + month + "." + day
                    time = hour + "." + minute + "." + second
                    return (date, time)
                # if it didn't match
                else:
                    print (None, None)





##################################################################
#                           EXECUTION                            #
##################################################################

# run
main = Main()
main.run()




################################
# How to setup the environment #
################################
# TODO should have a .sh script to set this up
# sudo apt-get update
# sudo apt install python3-pip
# pip install hachoir
# pip install PILLOW


# TODO
# * Create a Validator class that before renaming checks stuff like "Is the date we're trying to rename bigger than file creation date? If so, don't move, that's odd"
#   * more case: Is the date in the future? e.g. 2050? If so, don't move