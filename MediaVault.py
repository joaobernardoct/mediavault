import argparse
import csv
import os
import re
import sys
import shutil
from abc import ABC, abstractmethod
from datetime import datetime, timedelta      # utils date
from hachoir.parser import createParser       # utils video
from hachoir.metadata import extractMetadata  # utils video
from PIL import Image as PILImage             # utils image
from PIL.ExifTags import TAGS                 # utils image




##################################################################
# GENERAL SETTINGS
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
NR_IMAGES_PER_DAY = 15
WEE_SMALL_HOURS_OF_THE_MORNING = "04.00.00"

# Store photos in monthly folders inside of the yearly folder
# i.e. store photos in YYYY/MM if true / YYYY if false
MONTHLY_PARTITION = True

# Whether we should also traverse subdirs. It is safer to be turned off
TRAVERSE_SUBDIRS = True

# Debug mode (increased verbosity)
DEBUG = True




##################################################################
# MACROS
##################################################################
EXIF_STANDARD_CREATION_DATE = 1998

DATE_FORMAT = "%Y.%m.%d"
TIME_FORMAT = "%H.%M.%S"
OUTPUT_FORMAT = "%Y.%m.%d (%Hh%Mm%Ss)" # This represents how the images will be renamed
OUTPUT_FORMAT_REGEX = r"(\d{4}\.\d{2}\.\d{2}) \((\d{2}h\d{2}m\d{2}s)\)"




##################################################################
# MEDIA VAULT
##################################################################
class MediaVault():
    def __init__(self):
        self.organizer = Organizer()

    def run(self):
        print("Starting to process...")
        for root, dirs, files in os.walk('.'):
            for filename in sorted(files):
                if(DEBUG):
                    print("\n---Scanning: " + filename)
                file = os.path.join(root, filename)
                self.organizer.ingestFile(file)

            if not TRAVERSE_SUBDIRS:
                break

        self.organizer.organize()

        print("\nSuccess ;)")




########################################################################
# ORGANIZER
#                                                                      #
# 1st: .ingestFile - Ingest a file and process it, i.e. store the      #
#                    file path, capture date and capture time on a csv #
# 2nd: .organize - Rename and organize photos into folders using the   #
#                  generated csv content                               #
########################################################################
class Organizer():
    def __init__(self):
        # instantiate necessary classes
        self.mediaProcessorFactory = MediaProcessorFactory()
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


    def ingestFile(self, file_path):
        ''' The entrypoint for individual file processing '''
        # Ask MediaProcessorFactory for a processor to process the file
        try:
            processor = self.mediaProcessorFactory.create_processor(file_path)
            capture_date = processor.process(file_path)
        except (MediaProcessor.FileTypeNotSupportedException , MediaProcessor.CouldNotExtractCaptureDateException) as e:
            if (DEBUG):
                print("Exception: ", e)
            # File could not be processed
            return
        
        date = capture_date[0]
        time = capture_date[1]
        file_abs_path = os.path.abspath(file_path)

        # Store file information into csv
        fileDataToPersistOnCSV = {
            'OriginalPath': file_abs_path,
            'CaptureDate': date,
            'CaptureTime': time,
            'NewPath' : ''
        }
        self.mediaVaultCsv.write(fileDataToPersistOnCSV)

        # Additionally, update the dateCounter
        dateToCount = self.weeSmallHoursOfTheMorning(date, time)
        self.dateCounter[dateToCount] = self.dateCounter.get(dateToCount, 0) + 1
        # TODO BAH - This is horrible, we have a method of one class that writes into other class and then reads back?!  


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
            relativeDate  = self.weeSmallHoursOfTheMorning(date, time)
            relativeYear  = relativeDate[:4]
            relativeMonth = relativeDate[5:7]

            # Calculate the new file location and create the necessary folder structure
            if(MONTHLY_PARTITION):
                newFileLocation = self.processedFolder + relativeYear + "/" + relativeMonth + "/"  # .../YYYY/MM
            else:
                newFileLocation = self.processedFolder + relativeYear + "/"     # .../YYYY
            if self.dateCounter.get(relativeDate, 0) >= NR_IMAGES_PER_DAY:
                newFileLocation += relativeDate + "/"                       # .../YYYY/MM/YYYY.MM.DD
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

        timeFormatted         = datetime.strptime(time, TIME_FORMAT)
        timeEndOfDayFormatted = datetime.strptime(WEE_SMALL_HOURS_OF_THE_MORNING , TIME_FORMAT)
        time_difference = abs( int( (timeFormatted - timeEndOfDayFormatted).days ) )
        date = str( (datetime.strptime(date, DATE_FORMAT) - timedelta(days=time_difference)) ).replace("-",".")[:10]
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
# MEDIA VAULT CSV
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

        # TODO BAH - do we really need headers here to then skip the first row on organizer.organize()? rethink this, looks awful
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
# MEDIA PROCESSOR
##################################################################
class MediaProcessor(ABC):
    class FileTypeNotSupportedException(Exception):
        ''' This exception will be raised if no subclass can process the file '''
        pass

    class CouldNotExtractCaptureDateException(Exception):
        ''' This exception will be raised if the capture date could not be extracted '''
        pass

    @abstractmethod
    def process(self, file_path):
        """
        Process a given file.
        """
        pass

    @abstractmethod
    def is_supported(self, file_path):
        """
        Check if the file is of supported media type.
        """
        pass

    @abstractmethod
    def get_capture_date(self, file_path):
        """
        Extract capture date from the media file.
        """
        pass
        
    def is_valid_datetime(self, date, time=None):
        if date is None:
            return False
        try:
            # Parse date and time
            datetime_str    = f"{date} {time}" if time else date
            datetime_format = f"{DATE_FORMAT} {TIME_FORMAT}" if time else DATE_FORMAT
            datetime_obj    = datetime.strptime(datetime_str, datetime_format)
            # Ensure the date is within a reasonable range
            if datetime_obj.year < 1990 or datetime_obj > datetime.now():
                return False
            return True
        except ValueError:
            return False

    def im_feeling_lucky(self, file_path):
        ''' if the capture date fails to be retrieved from the file's metadata,
            this method will try to retrieve it from the filename '''
        filename = os.path.basename(file_path)
        SEARCH_PATTERNS_LIST = [
            r'IMG_(\d{4})(\d{2})(\d{2})',  # Whatsapp image or video
            r'IMG-(\d{4})(\d{2})(\d{2})',   # Idk
            r'VID-(\d{4})(\d{2})(\d{2})',   # Idk
            r'WhatsApp Image (\d{4})-(\d{2})-(\d{2}) at (\d{2})\.(\d{2})\.(\d{2})',  # Whatsapp image (old)
            r'WhatsApp Video (\d{4})-(\d{2})-(\d{2}) at (\d{2})\.(\d{2})\.(\d{2})',  # Whatsapp video (old)
            r'Screenshot_(\d{4})(\d{2})(\d{2})-(\d{2})(\d{2})(\d{2})',   # Samsung phone screenshots
            r'(\d{4})(\d{2})(\d{2})_(\d{2})(\d{2})(\d{2})',   # Samsung phone camera roll
            r'(\d{4})\.(\d{2})\.(\d{2}) \((\d{2})h(\d{2})m(\d{2})s\)'  # This script (so it is idempotent)
        ]
        for pattern in SEARCH_PATTERNS_LIST:
            match = re.search(pattern, filename)
            if match:
                groups = match.groups()
                if len(groups) == 3:  # if it matched a date
                    year, month, day = groups
                    date = f"{year}.{month}.{day}"
                    time = None
                elif len(groups) == 6:  # if it matched a date and a time
                    year, month, day, hour, minute, second = groups
                    date = f"{year}.{month}.{day}"
                    time = f"{hour}.{minute}.{second}"
                if self.is_valid_datetime(date, time):
                    return (date, time)
        # Exit gracefully
        raise MediaProcessor.CouldNotExtractCaptureDateException("Could not extract a capture date")



##################################################################
# MEDIA PROCESSOR FACTORY
##################################################################
class MediaProcessorFactory:
    @staticmethod
    def create_processor(file_path):
        if ImageProcessor().is_supported(file_path):
            return ImageProcessor()
        elif VideoProcessor().is_supported(file_path):
            return VideoProcessor()
        else:
            raise MediaProcessor.FileTypeNotSupportedException("File type is not supported")




##################################################################
# MEDIA PROCESSOR >> IMAGE PROCESSOR
##################################################################
class ImageProcessor(MediaProcessor):
    def process(self, file_path):
        if not self.is_supported(file_path):
            raise MediaProcessor.FileTypeNotSupportedException("File type is not supported")
        return self.get_capture_date(file_path)

    def is_supported(self, file_path):
        '''
        Check if file is supported (i.e. an image)
        '''
        try:
            PILImage.open(file_path)
            return True
        except (IOError, SyntaxError):
            return False

    def get_capture_date(self, file_path):
        try:
            image = PILImage.open(file_path)
            for tag_id, value in image._getexif().items():
                if TAGS.get(tag_id, tag_id) == "DateTimeOriginal":
                    capture_date = str(value)
                    if capture_date:
                        capture_date = datetime.strptime(capture_date, "%Y:%m:%d %H:%M:%S")
                        date = capture_date.strftime(DATE_FORMAT)
                        time = capture_date.strftime(TIME_FORMAT)
                        if self.is_valid_datetime(date, time):
                            return (date, time)
        except Exception as e:
            # Handle all exceptions gracefully
            pass

        # Delegate to im_feeling_lucky or just assume a capture date was not found
        if (IM_FEELING_LUCKY):
            self.im_feeling_lucky(file_path)
        else:
            raise MediaProcessor.CouldNotExtractCaptureDateException("Could not extract a capture date")




##################################################################
# MEDIA PROCESSOR >> VIDEO PROCESSOR
##################################################################
class VideoProcessor(MediaProcessor):
    def process(self, file_path):
        if not self.is_supported(file_path):
            raise MediaProcessor.FileTypeNotSupportedException("File type is not supported")
        return self.get_capture_date(file_path)
        if self.is_supported(file_path):
            return self
        else:
            return None

    def is_supported(self, file_path):
        '''
        Check if file is supported (i.e. a video)
        Current support only includes video formats that typically store capture dates in the format "%Y-%m-%d %H:%M:%S"
        '''
        SUPPORTED_VIDEO_EXTENSIONS = ['.mp4', '.mov', '.mkv', '.avi', '.flv', '.webm', '.m4v']
        file_extension = os.path.splitext(file_path)[1].lower()
        return file_extension in SUPPORTED_VIDEO_EXTENSIONS

    def get_capture_date(self, file_path):
        try:
            capture_date = str(extractMetadata(createParser(file_path)).get('creation_date'))
            if capture_date:
                capture_date = datetime.strptime(capture_date, "%Y-%m-%d %H:%M:%S")
                date = capture_date.strftime(DATE_FORMAT)
                time = capture_date.strftime(TIME_FORMAT)
                if self.is_valid_datetime(date, time):
                    return (date, time)
        except Exception as e:
            # Handle all exceptions gracefully
            pass

        # Delegate to im_feeling_lucky or just assume a capture date was not found
        if (IM_FEELING_LUCKY):
            self.im_feeling_lucky(file_path)
        else:
            raise MediaProcessor.CouldNotExtractCaptureDateException("Could not extract a capture date")




##################################################################
# REVERT
##################################################################
class Revert():
    def run(self):
        '''
        This mode reverts the operations of MediaVault.py, restoring all new file paths to their previous state. 
        If you only want to revert some of the changes, move all the files you 
        don't want to revert to a separate folder before running.
        '''
        print("Starting revert operation...")
        with open("./_Media Vault/_log.md", 'r') as file:
            content = file.readlines()
            for line in content:
                # Split the line by the pipe character '|'
                parts = [part.strip() for part in line.split("|") if part.strip()]
                # Extract the values
                old_path = parts[0]
                new_path = parts[1]
                # Try to revert (new_path --> old_path)
                try:
                    if os.path.exists(new_path):
                        os.rename(new_path, old_path)
                        print(f"Renamed {new_path} to {old_path}")
                    else:
                        # File does not exist
                        pass
                except Exception as e:
                    print(f"An error occurred while processing {new_path}: {e}")




##################################################################
# EXECUTION
##################################################################
def main():
    parser = argparse.ArgumentParser(description="Media Vault Script")
    parser.add_argument("--revert", "-r", action="store_true", help="revert the operation")
    args = parser.parse_args()

    if args.revert:
        revert = Revert()
        revert.run()
    else:
        mediaVault = MediaVault()
        mediaVault.run()




if __name__ == "__main__":
    main()
