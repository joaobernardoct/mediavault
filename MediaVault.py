import shutil
import os


##########################################################
#                    GENERAL SETTINGS                    #
##########################################################

'''
NR_IMAGES_PER_DAY (int)
   > if the number of images in a day is > NR_IMAGES_PER_DAY they will be placed in a folder
   > default is 9999 (does not create those folders) / recommended is 15
'''
NR_IMAGES_PER_DAY = 9999

'''
WEE_SMALL_HOURS_OF_THE_MORNING (int)
   > sets the end of a day - e.g. photos at 03:00 usually relate to the end of the previous day  
                                  and not the beggining of the next
   > this does not change the date of the photo itself, it is only used when creating folders 
   > default is 0 (midnight) / recommended is 4
'''
WEE_SMALL_HOURS_OF_THE_MORNING = 0



##########################################################
#                   DEVELOPER SETTINGS                   #
##########################################################

'''
ALLOWED_EXTENSIONS (list)
> allowed image/video extensions
'''
ALLOWED_EXTENSIONS = ['jpeg', 'jpg', 'mp4']

'''
TIME_SAVED (int - in seconds)
> time saved per image - assumption is each image would take 10 seconds manually to rename
'''
TIME_SAVED = 10 / 60

##########################################################
#                          MAIN                          #
##########################################################

class Main():
    def __init__(self):
        # instantiates an ImageUtils
        self.img_handler = ImageHandler()


    def create_auxiliar_folders(self):
        os.makedirs("./" + "unprocessed", exist_ok=True) 


    def run(self):
        '''
        traverses the provided directory and processes each image found
        '''
        # traverse each file and rename it
        for filename in sorted(os.listdir(os.getcwd())):
            self.img_handler.run(filename)
        # move files into folders
        self.img_handler.organize()
        # end and display output
        self.img_handler.output()


##########################################################
#                     IMAGE HANDLER                      #
##########################################################

class ImageHandler():
    '''
    This is an auxiliar function for Main
    '''

    def __init__(self):
        # keeps tracked of number of images with the same date 
        self.date_counter = {}
        # instantiates an ImageUtils
        self.utils = ImageUtils()
        # counter [processed, unprocessed] to display stats in the end
        self.processing_counter = [0,0]


    def run(self, filename):
        extension = filename.split('.')[-1]
        if extension in ALLOWED_EXTENSIONS:
            new_name = self.utils.get_date_from_filename(filename)
            date = new_name[0]
            time = new_name[1]
            if date == "UNSUPPORTED_FORMAT":
                shutil.move(os.path.join(".", filename), "./unprocessed")
                self.processing_counter[1] += 1
            else:
                self.rename(date, time, filename, extension)
                self.processing_counter[0] += 1


    def rename(self, date, time, filename, extension):
        # keep track of parsed date on date_counter
        self.date_counter[date] = self.date_counter.get(date, 0) + 1
        # define new name for file
        new_name = date + ' (' + str(self.date_counter.get(date)) + ')'
        if not time == "NA":
            new_name += ' - ' + time
        # ensure file does not exist (avoid overwriting) and rename
        if not (os.path.isfile(new_name + "." + extension)):
            os.rename(filename, new_name + "." + extension)
        else:
            print("Error while storing " + new_name + "." + extension + ". File already exists.")    


    def organize(self):
        '''
        (1) if the number of images for one day is >= NR_IMAGES_PER_DAY images
            they will be moved into a new folder (for that day)
        '''
        # dictionary { DATE : FOLDER_PATH }
        created_folders = {}
        # iterate through date_counter to understand which dates will be moved
        for date in self.date_counter:
            count = self.date_counter.get(date)
            if count >= NR_IMAGES_PER_DAY:
                # create folder
                os.mkdir("./" + date)
                # add date to list of created folders
                created_folders[date] = created_folders.get(date, "") + "./" + date

        # list all files in dir
        list_dir = os.listdir("./")

        # move files that have their name "blacklisted" on created_folders to the corresponding folder
        for filename in list_dir:
            for date in created_folders:
                if (filename.startswith(date)):
                    # check if file has time
                    if (len(filename) > 12 and filename.split('.')[-2][-9:-7].isdigit()):
                        # if so, check hour
                        hour = int(filename.split('.')[-2][-9:-7])
                        # images prior to WEE_SMALL_HOURS_OF_THE_MORNING are not moved
                        if (hour <= WEE_SMALL_HOURS_OF_THE_MORNING): # TODO: TEST THIS
                            continue
                    shutil.move(os.path.join(".", filename), created_folders.get(date))


    def output(self):
        print("Store Images: successfully renamed files.")
        print("Processed images:     " + str(self.processing_counter[0]))
        print("Unprocessed images:   " + str(self.processing_counter[1]))
        print("Time saved (minutes): " + str(self.processing_counter[0] * TIME_SAVED) )


##########################################################
#                      IMAGE UTILS                       #
##########################################################

class ImageUtils():
    '''
    This is an auxiliar function for ImageHandler
    '''

    def __init__(self):
        pass


    def get_date_from_filename(self, filename):
        '''
        (1) Parses the filename to extract the date as a string   
        '''
        if filename.startswith("IMG-") or filename.startswith("VID"): # WHATSAPP IMAGES 
            date = filename[4:8] + '.' + filename[8:10] + '.' + filename[10:12]
            time = ''

        elif filename.startswith("IMG_"): # I DON'T KNOW
            date = filename[4:8] + '.' + filename[8:10] + '.' + filename[10:12]
            time = filename[13:15] + 'h' + filename[15:17] + 'm' + filename[17:19] + 's'

        elif filename.startswith("Screenshot_"): # SCREENSHOT IMAGES
            date = filename[11:15] + '.' + filename[15:17] + '.' + filename[17:19]
            time = ''
            
        elif filename.startswith("19") or filename.startswith("20"): # IMAGES STARTING WITH THE DATE (JOAO'S PHONE CAMERA ROLL)
            date = filename[0:4] + '.' + filename[4:6] + '.' + filename[6:8]
            time = filename[9:11] + 'h' + filename[11:13] + 'm' + filename[13:15] + 's'
        
        # WE CAN ADD MORE FILENAME FORMATS HERE

        else:
            date = "UNSUPPORTED_FORMAT"
            time = ''
        
        '''
        (2) Check if "date" (format: YYYY.MM.DD) is actually a date
        '''
        try:
            if len(date) == 10:
                is_year   = 1960 <= int(date[0:4])  <= 2100
                is_month  = 1    <= int(date[5:7])  <= 12
                is_day    = 1    <= int(date[8:10]) <= 31
                is_date   = is_year + is_month + is_day
            else: 
                is_date   = False
        except ValueError:
            is_date       = False

        '''
        (3) Check if "time" (format: HHhMMmSSs) is actually a time
        '''
        try:
            if len(time) == 9:
                is_hour   = 0    <= int(time[0:2])  <= 23
                is_minute = 0    <= int(time[3:5])  <= 59
                is_second = 0    <= int(time[6:8])  <= 59
                is_time   = is_hour + is_minute + is_second
            else:
                is_time   = False
        except ValueError:
            is_date       = False

        '''
        (4) Return
        '''     
        if is_date and is_time:
            return (date,time)
        elif is_date:
            return (date,'NA')
        else:
            return ("UNSUPPORTED_FORMAT","NA")



##########################################################
#                       EXECUTION                        #
##########################################################

# set custom variables
NR_IMAGES_PER_DAY = 15
WEE_SMALL_HOURS_OF_THE_MORNING = 4

# run
main = Main()
main.create_auxiliar_folders()
main.run()
