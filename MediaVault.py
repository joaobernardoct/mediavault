import os
import re
import shutil
from datetime import datetime, timedelta      # utils date 
from hachoir.parser import createParser       # utils video
from hachoir.metadata import extractMetadata  # utils video
from PIL import Image                         # utils image
from PIL.ExifTags import TAGS                 # utils image




##################################################################
#                        GENERAL SETTINGS                        #
##################################################################

# if the number of images in a day is > NR_IMAGES_PER_DAY they will be placed in a folder
NR_IMAGES_PER_DAY = 10

# sets the end of a day
# > e.g. photos at 03:00 usually relate to the end of the previous day and not the beggining of the next
# > this does not change the date of the photo itself, it is only used when creating folders 
WEE_SMALL_HOURS_OF_THE_MORNING = datetime.strptime("04.00.00", "%H.%M.%S")

# TODO FORMAT (descrever cada variavel abaixo)
# essas variaveis devia ser uma lista e a pessoa escolhe o indice do formato e.g. OUTPUT_FORMAT[1] então usa também OUTPUT_FORMAT_REGEX[1]
# no fundo o que é "GENERAL SETTING" é só a macro "CHOSEN_FORMAT = 1" e depois as duas vars abaixo vão ser usadas assim
#
OUTPUT_FORMAT = "%Y.%m.%d (%Hh%Mm%Ss)"
OUTPUT_FORMAT_REGEX = "r'^\d{4}\.\d{2}\.\d{2} \(\d{2}h\d{2}m\d{2}s\)$'"

# README file under the unprocessed images and videos folder 
UNPROCESSED_FOLDER_README = '''
    This folder includes all unprocessed files. 
    
    IMAGES:
        The images supported follow the EXIF standard, which defines specific metadata 
            tags for digital images taken by cameras or other imaging devices.
    
        These includes (not extensively):
            .jpg (JPEG)
            .tif or .tiff (Tagged Image File Format)
            .gif (Graphics Interchange Format)
            .bmp (Bitmap Image File)
            .raw (Camera RAW Image File)
            .cr2 (Canon RAW Image File)
            .nef (Nikon RAW Image File)
            .orf (Olympus RAW Image File)
            .arw (Sony RAW Image File)
            .rw2 (Panasonic RAW Image File)
            .dng (Digital Negative Image File)
            .jpeg (JPEG)
            .heic (High Efficiency Image Format)
            .heif (High Efficiency Image Format).

        These excludes (not extensively):
            .png (Portable Network Graphics)


    VIDEOS:
        The videos supported, whilst not following a specific standard, include capture date
            metadata in the format "%Y-%m-%d %H:%M:%S".

        These includes (not extensively):
            .mp4 (MP4)
            .mov (QuickTime)
            .mkv (Matroska)
            .avi (AVI)
            .flv (Flash Video)
            .webm (WebM)
            .m4v (M4V)


    Support for additional extensions might be considered in the future.
    Joao
    2023 
    '''
    
# README file under the other files folder 
OTHER_FILES_FOLDER_README = '''
    This folder includes all files that are neither images nor videos. 
    

    Support for additional file types (e.g. audio) might be considered in the future.
    Joao
    2023 
    '''




##################################################################
#                            MAIN                                #
##################################################################
class Main():
    def __init__(self):
        self.imageHandler = ImageHandler()
        self.videoHandler = VideoHandler()
        self.imgs_per_date = {}       # tracks the number of images per date (to organize into folders) 


    def create_auxiliar_structures(self):
        # Structure for unprocessed images and videos
        os.makedirs("./_Unprocessed images and videos", exist_ok=True)
        try:
            with open("./_Unprocessed images and videos/README.txt", 'w') as file:
                file.write(UNPROCESSED_FOLDER_README)
        except Exception as e:
            pass

        # Structure for unsupported files
        os.makedirs("./_Other files", exist_ok=True)
        try:
            with open("./_Other files/README.txt", 'w') as file:
                file.write(OTHER_FILES_FOLDER_README)
        except Exception as e:
            pass


    def rename(self, filename, capture_date):
            '''
            capture date should follow the format "YYYY.MM.DD (HHhMMmSSs)"
            '''

            # ensure date is in the correct format. else, move to unprocessed
            invalid_format = False
            if capture_date is None:
                invalid_format = True
            elif re.match(OUTPUT_FORMAT_REGEX, capture_date) is None:
                invalid_format = True
            elif int(capture_date[:4]) < 1998: # EXIF standard's creation date
                invalid_format = True
            if invalid_format:
                shutil.move(os.path.join(".", filename), "./_Unprocessed images and videos")
                return

            # ensure the new filename does not yet exist
            counter = 1
            extension = os.path.splitext(filename)[1]
            unique_new_filename = f"{capture_date}{extension}"
            while (os.path.exists(unique_new_filename)):
                unique_new_filename = f"{capture_date} ({counter}){extension}"
                counter += 1

            if not (os.path.exists(unique_new_filename)):
                # rename image with new_filename
                os.rename(filename, unique_new_filename)
                # increase date counter
                date = unique_new_filename[:10]
                self.imgs_per_date[date] = self.imgs_per_date.get(date, 0) + 1


    def organize(self):
        for filename in os.listdir("./"):
            if not len(filename) > 20 or not os.path.isfile(filename):
                continue
            date = filename[:10]
            hour = filename[12:14] + "." + filename[15:17] + "." + filename[18:20] # TODO FORMAT - Hour depende de output format. deve ser convertida em HH.MM.SS
                                                                                    # usar datetime para converter de output format para YYYY.MM.DD HH.MM.SS e depois parse that
            # the next 2 lines are really cool ;)
            # the folder in which the image goes to is calculated based on WEE_SMALL_HOURS_OF_THE_MORNING
            time_difference = abs( int( (datetime.strptime(hour, "%H.%M.%S") - WEE_SMALL_HOURS_OF_THE_MORNING).days ) )
            date = str( (datetime.strptime(date, "%Y.%m.%d") - timedelta(days=time_difference)) ).replace("-",".")[:10]
            if self.imgs_per_date.get(date, 0) >= NR_IMAGES_PER_DAY:
                os.makedirs("./" + date, exist_ok=True)
                # move
                shutil.move(os.path.join(".", filename), "./" + date)
    

    def display_output(self):
        print("Store Images: successfully renamed files.")
        processed_count = len([file for file in os.listdir("./") if os.path.isfile(os.path.join("./", file))])
        print("Processed images:     " + str(processed_count))
        unprocessed_count = len([file for file in os.listdir("./_Unprocessed images and videos") if os.path.isfile(os.path.join("./_Unprocessed images and videos", file))])
        unprocessed_count += len([file for file in os.listdir("./_Other files") if os.path.isfile(os.path.join("./_Other files", file))])
        print("Unprocessed images:   " + str(unprocessed_count))
        seconds = processed_count * 10 / 60
        time_saved = "{:02d}:{:02d}".format( int((seconds % 3600) // 60) , int(seconds % 60) ) # TODO: Add days (ask ChatGPT)
        print("Time saved (HH:MM):   " + time_saved) # assumption: each img takes 10 sec to rename manually


    def run(self):
        # (1) CREATE AUXILIAR files and folders
        self.create_auxiliar_structures()

        # (2) TRAVERSE each file and rename it
        for filename in sorted(os.listdir(os.getcwd())):

            # process an image
            if self.imageHandler.is_image(filename):
                capture_date = self.imageHandler.get_image_capture_date(filename)
                self.rename(filename, capture_date)

            # process a video
            elif self.videoHandler.is_video(filename):
                capture_date = self.videoHandler.get_video_capture_date(filename)   
                self.rename(filename, capture_date)

            # process everything else
            else:
                if (os.path.isfile(filename) and filename != "StoreArtifacts.py"):
                    shutil.move(os.path.join(".", filename), "./_Other files")


        # (3) ORGANIZE files into folders
        self.organize()

        # (4) FINISH and display output
        self.display_output()




##################################################################
#                          IMAGE HANDLER                         #
#                                                                #
#  Is called by main to retrieve the capture date from an image  #
##################################################################
class ImageHandler():

    def is_image(self, file_path):
        try:
            Image.open(file_path)
            return True
        except (IOError, SyntaxError):
            return False

    # either returns the capture date as a string in format "YYYY.MM.DD (HHhMMmSSs)" or None
    def get_image_capture_date(self, image_path):
        # retrieve capture date
        try:
            image = Image.open(image_path)
            exif_data = image._getexif()
            for tag_id, value in exif_data.items():
                tag_name = TAGS.get(tag_id, tag_id)
                if tag_name == "DateTimeOriginal":

                    capture_date = str(value).replace(":", ".")
                    input_format = "%Y.%m.%d %H.%M.%S"
                    return str(datetime.strptime(capture_date, input_format).strftime(OUTPUT_FORMAT))

        except (AttributeError, KeyError, IndexError):
            pass

        return None       








##################################################################
#                          VIDEO HANDLER                         #
#                                                                #
#  Is called by main to retrieve the capture date from a video   #
##################################################################
class VideoHandler():

    def is_video(self, video_path):
        # only allow video formats that typically store capture dates in the format "%Y-%m-%d %H:%M:%S"
        video_extensions = ['.mp4', '.mov', '.mkv', '.avi', '.flv', '.webm', '.m4v']
        file_extension = os.path.splitext(video_path)[1].lower()
        return file_extension in video_extensions

    # either returns the capture date as a string in format "YYYY.MM.DD (HHhMMmSSs)" or None
    def get_video_capture_date(self, video_path):
        # retrieve capture date
        try:

            parser = createParser(video_path)
            capture_date = str(extractMetadata(parser).get('creation_date')).replace("-", ".").replace(":", ".")
            input_format = "%Y.%m.%d %H.%M.%S"
            return str(datetime.strptime(capture_date, input_format).strftime(OUTPUT_FORMAT))
        
        except Exception as e:
            pass

        return None



##################################################################
#                           EXECUTION                            #
##################################################################

# run
main = Main()
main.run()

'''
#TODO
O formato em que renomeia as fotos devia ser uma macro e devia ser possível escolher entre três tipos diferentes. Seria mesmo fácil
porque só é usado em três sitios que vão ficar identificados com #TODO FORMAT

Esta lógica deve ser bem pensada para o código ser mais easy e fácil de alterar no futuro tbh

Acho que se podia criar uma classe "DateUtils" em que tudo o que é datas é processado lá e 
basta dar-se a string com a data e uma string com o formato em que está a data
'''