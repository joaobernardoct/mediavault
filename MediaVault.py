######################################################################################################
##              Alterar o nome das fotos/videos do whatsapp para o formato AAAA-MM-DD               ##
##                                IMG-20190921-WA0064 --> 2019.09.21                                ##
##                                                                                                  ##
##   1 Garantir que a diretoria apenas contém fotos/videos do whatsapp                              ##
##   2 Correr este programa nessa diretoria                                                         ##
##                                                                                                  ##
##                                                                       Joao Bernardo 2019.09.21   ##
##                                                                                                  ##
##   Nota: A 2020.09.10 aumentei o script para funcionar nos Screenshots também                     ##
##   Nota: A 2021.01.14 aumentei o script para funcionar em ficheiros que comecem com a data        ##
##   TODO: Há imenso código repetido -- otimizar (talvez com classes)                               ##
##   TODO: Até agora eu tenho de selecionar ficheiros que correspondam a um tipo de norma e pô-los ##
##         noutra pasta e fazer "batch" a "batch". Era fixe poder ter uma pasta com varios tipos    ##
##         de nomenclatura e extensões e que iterava BEM por todos os ficheiros. Sem comer nenhum   ##
##         e mantendo sempre bem o (2) (3) (4) para ficheiros do mesmo dia.                         ##
##   TODO: Ficheiros até às 5h da manhã deviam ficar com a data do dia anterior.                    ##
######################################################################################################
import os

last_name = "idk"
i = 1

user_confirmation = None #2021.01.14 flag to remember user choice

for filename in sorted(os.listdir(os.getcwd())):
    if ( filename.startswith("IMG") or filename.startswith("VID") ):
        if filename.endswith(".jpeg"): #
            ext = ".jpeg"              #
        elif filename.endswith(".jpg"):#
            ext = ".jpg"               #
        elif filename.endswith(".mp4"):#
            ext = ".mp4"               #
        else:                          #
            break                      #

        if last_name == filename[4:12]:
            i += 1
        else:
            i = 1
        new_name = filename[4:8] + '.' + filename[8:10] + '.' + filename[10:12] + ' (' + str(i) + ')'
        os.rename(filename, new_name + ext)
        last_name = filename[4:12]

    if ( filename.startswith("Screenshot_")):
        if filename.endswith(".jpeg"): #
            ext = ".jpeg"              #
        elif filename.endswith(".jpg"):#
            ext = ".jpg"               #
        elif filename.endswith(".mp4"):#
            ext = ".mp4"               #
        else:                          #
            break                      #
    
        new_name = filename[11:15] + '.' + filename[15:17] + '.' + filename[17:19]

        if last_name == new_name:
            i += 1
        else:
            i = 1

        os.rename(filename, new_name + ' (' + str(i) + ')' + ext)
        last_name = new_name

    if(filename.startswith("20")):
        if (user_confirmation) == None:
            user_confirmation = input("Do the first 8 characters of the filename correspond to the date? (y/n)")
        if(user_confirmation == 'Y' or user_confirmation == 'y'):
            if filename.endswith(".jpeg"): #
                ext = ".jpeg"              #
            elif filename.endswith(".jpg"):#
                ext = ".jpg"               #
            elif filename.endswith(".mp4"):#
                ext = ".mp4"               #
            else:                          #
                break                      #

            new_name = filename[0:4] + '.' + filename[4:6] + '.' + filename[6:8]

            if last_name == new_name:
                i += 1
            else:
                i = 1

            os.rename(filename, new_name + ' (' + str(i) + ')' + ext)
            last_name = new_name
print("nome dos ficheiros alterado com sucesso")
######################################################################################################