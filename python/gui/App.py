''' TODO:
TEST - image rotation control
- image from folder button 
- file system
'''


import tkinter as tk
from tkinter import filedialog
from collections import defaultdict
import time
import numpy as np
import cv2
import PIL.Image, PIL.ImageTk
import tifffile as tif

import os
os.chdir(r'C:\Users\cell_ml\Downloads\SmartScope\python\gui')
import sys
sys.path.append('..\\source\\maskrcnn')
sys.path.append('..\\source\\dataset')
sys.path.append('..\\source\\miq')
sys.path.append('..\\source')
sys.path.append('C:\\Program Files\\Micro-Manager-2.0beta')
 
import utils
import model as modellib
import visualize
import config

import mark_dataset
import alignment
import time
 
import chip
import position as pos
import focus
import sc_utils
import run
 
class Entry_Option:
    def __init__(self, master, label, default):
        self.label = label
        self.default = default
        self.entry = tk.StringVar(master, value=self.default)
        
 
class Live_Camera:
    def __init__(self, window):
        self.window = window
        self.window.title("Live Camera")
        self.window.protocol('WM_DELETE_WINDOW', self.delete)

        # Camera Scale
        scale = 3
        self.width = int(CAMERA_PIXELS[1] / scale)
        self.height = int(CAMERA_PIXELS[0] / scale)
        self.dim = (self.width, self.height)

        self.vid = MyVideoCapture()
        self.canvas = tk.Canvas(window, width = self.width, height = self.height)
        self.canvas.pack()

        # Button that lets the user take a snapshot
        self.btn_snapshot=tk.Button(window, text="Snapshot", width=50, command=self.snapshot)
        self.btn_snapshot.pack(anchor=tk.CENTER, expand=True)

        # After it is called once, the update method will be automatically called every delay milliseconds
        self.delay = 15
        self.update()

    def snapshot(self):
        frame = self.vid.get_frame()
        frame = np.flipud(frame)
        tif.imwrite(time.strftime("%Y%m%d%H%M%S") + '.tif', frame)

    def update(self):
        frame = self.vid.get_frame()
        frame = cv2.resize(frame, self.dim, interpolation=cv2.INTER_AREA)
        img8 = (frame/4).astype('uint8')
        frame = PIL.Image.fromarray(img8)
        self.photo = PIL.ImageTk.PhotoImage(image = frame)
        self.canvas.create_image(0, 0, image = self.photo, anchor = tk.NW)
        self.window.after(self.delay, self.update)
    
    def delete(self):
        self.vid.__del__()
        self.window.destroy()


class MyVideoCapture:
    def __init__(self):
        self.cam = sc_utils.start_cam()

    def get_frame(self):
        frame = self.cam.get_frame(exp_time=1).reshape(self.cam.sensor_size[::-1])
        return frame

    def __del__(self):
        try:
            sc_utils.close_cam(self.cam)
        except:
            print ('could not close camera')
            pass
 
 
class ExpParmas:
 
    def __init__(self, master):
        self.master = master
        self.master.title("Imaging Parameters")
        self.advanced_visible = False
        self.live_class = None
 
        self.general_options =  [Entry_Option(self.master, 'Chip', self.get_default(0)),
                            Entry_Option(self.master, 'Objective', self.get_default(1)),
                            Entry_Option(self.master, 'Drug',self.get_default(2)),
                            Entry_Option(self.master, 'Cell',self.get_default(3)),
                            Entry_Option(self.master, 'Folder',self.get_default(4)),
                            Entry_Option(self.master, 'Start Date',time.strftime("%Y_%m_%d")),
                            Entry_Option(self.master, 'Drug Concentration',self.get_default(6)),
                            Entry_Option(self.master, 'Chip Index',self.get_default(7)),
                            Entry_Option(self.master, 'BFF Exposure (ms)',self.get_default(8)),
                            Entry_Option(self.master, 'DAP Exposure (ms)',self.get_default(9)),
                            Entry_Option(self.master, 'GFP Exposure (ms)',self.get_default(10)),
                            Entry_Option(self.master, 'TXR Exposure (ms)',self.get_default(11)),
                            Entry_Option(self.master, 'CY5 Exposure (ms)',self.get_default(12))]
 
        # TODO: Read defaults from conts.py
        self.advanced_options = [Entry_Option(self.master, 'Focus Step Size (um)',self.get_default(13)),
                            Entry_Option(self.master, 'Focus Inital Total Range (um)',self.get_default(14)),
                            Entry_Option(self.master, 'Focus Next Point Range (um)',self.get_default(15)),
                            Entry_Option(self.master, 'Focus Points X',self.get_default(16)),
                            Entry_Option(self.master, 'Focus Points Y',self.get_default(17)),
                            Entry_Option(self.master, 'Save JPGs (y/n)',self.get_default(18)),
                            Entry_Option(self.master, 'Alignment Model Name',self.get_default(19)),
                            Entry_Option(self.master, 'Image Rotation (0, 90, 180, 270)',self.get_default(20)),
                            Entry_Option(self.master, 'Apartments Per Image X',self.get_default(21)),
                            Entry_Option(self.master, 'Apartments Per Image Y',self.get_default(22)),
                            Entry_Option(self.master, 'Frame Width',self.get_default(23)),
                            Entry_Option(self.master, 'Frame Height',self.get_default(24)),
                            Entry_Option(self.master, 'Camera Pixel Width',self.get_default(25)),
                            Entry_Option(self.master, 'Camera Pixel Height',self.get_default(26))]
         
        self.mmc = sc_utils.get_mmc()
        self.setup_window()
 
    def setup_window(self):
        # Setup the possible choices
        self.chips = ["ML Chip", "KL Chip"]
        self.objectives = ['4x', '10x', '20x']
        self.filters =['bff_checkbox', 'dap_checkbox', 'gfp_checkbox', 
                       'txr_checkbox', 'cy5_checkbox']
        self.drugs = ["Quizartinib", "Imatinib", "DRUG A"]
        self.cells = ["MOLM13", "PC9", "CELL A"]
        self.units = ["fM", "pM", "nM", "uM"]
 
        # self.drop_selections = [tk.StringVar(self.master, value=self.general_options['Chip']),
        #                         tk.StringVar(self.master, value=self.general_options['Objective']),
        #                         tk.StringVar(self.master, value=self.general_options['Drug']),
        #                         tk.StringVar(self.master, value=self.general_options['Cell'])]
 
        self.general_labels = [self.make_label(val.label) for val in self.general_options]
        self.advanced_labels = [self.make_label(val.label) for val in self.advanced_options]
 
        # Layout the general options 
        for i, label in enumerate(self.general_labels):
            label.grid(row=i, column=0, columnspan=2)
 
        # Make dropdown menus
        self.chip_drop = tk.OptionMenu(self.master, self.general_options[0].entry, *self.chips)
        self.objective_drop = tk.OptionMenu(self.master, self.general_options[1].entry, *self.objectives)
        self.drug_drop = tk.OptionMenu(self.master, self.general_options[2].entry, *self.drugs)
        self.cell_drop = tk.OptionMenu(self.master, self.general_options[3].entry, *self.cells)
        self.chip_drop.grid(row=0, column=2, columnspan=2)
        self.objective_drop.grid(row=1, column=2, columnspan=2)
        self.drug_drop.grid(row=2, column=2, columnspan=2)
        self.cell_drop.grid(row=3, column=2, columnspan=2)
 
        # Make entry boxes
        self.entries = []
        for i, entry in enumerate(self.general_options):
            if i > 3:
                self.entries.append(self.make_entry(entry.default))
                self.entries[i-4].grid(row=i, column=2, columnspan=2)
        for i, entry in enumerate(self.advanced_options):
            self.entries.append(self.make_entry(entry.default))
             
 
        # Unit Dropdown
        self.unit_string = tk.StringVar(self.master, value='uM')
        self.unit_drop = tk.OptionMenu(self.master, self.unit_string, *self.units)
        self.unit_drop.grid(row=6, column=4)
 
        # Checkboxes
        self.bff_check = tk.BooleanVar()
        self.dap_check = tk.BooleanVar()
        self.gfp_check = tk.BooleanVar()
        self.txr_check = tk.BooleanVar()
        self.cy5_check = tk.BooleanVar()
        self.bff_checkbox = tk.Checkbutton(self.master, text='BFF', variable=self.bff_check, onvalue=True, offvalue=False)
        self.dap_checkbox = tk.Checkbutton(self.master, text='DAP', variable=self.dap_check, onvalue=True, offvalue=False)
        self.gfp_checkbox = tk.Checkbutton(self.master, text='GFP', variable=self.gfp_check, onvalue=True, offvalue=False)
        self.txr_checkbox = tk.Checkbutton(self.master, text='TXR', variable=self.txr_check, onvalue=True, offvalue=False)
        self.cy5_checkbox = tk.Checkbutton(self.master, text='CY5', variable=self.cy5_check, onvalue=True, offvalue=False)
        self.bff_checkbox.grid(row=8, column=4)
        self.dap_checkbox.grid(row=9, column=4)
        self.gfp_checkbox.grid(row=10, column=4)
        self.txr_checkbox.grid(row=11, column=4)
        self.cy5_checkbox.grid(row=12, column=4)
 
        # Create the Buttons
        image_button = tk.Button(self.master, text='Start', command=self.image)
        browse_button = tk.Button(self.master, text='...', command=self.get_directory)
        advanced_button = tk.Button(self.master, text='Advanced Settings', command=self.advanced)
        self.save_button = tk.Button(self.master, text='Save Current Values As Defaults', command=self.save_defaults)
        browse_button.grid(row=4, column=4)
        image_button.grid(row=len(self.general_labels)+1, column=4, columnspan=1, sticky='e')
        advanced_button.grid(row=len(self.general_labels)+1, column=3, columnspan=1)
        live_camera = tk.Button(self.master, text='Live Camera', command=self.camera)
        live_camera.grid(row=len(self.general_labels)+1, column=2, columnspan=1)
 
    def camera(self):
        live_cam = tk.Toplevel(self.master)
        self.live_class = Live_Camera(live_cam)
        self.live_class.window.mainloop()

    def get_directory(self):
        folder = filedialog.askdirectory()
        self.set_entry_text(self.entries[0], folder)
        return
    
    def save_defaults(self):
        # Save the current vals to default.txt
        with open('default.txt', 'w') as file:
            for i, val in enumerate(self.general_options):
                if i < 4:
                    print(f"{val.entry.get()}", file=file)
            for val in self.entries:
                print(f"{val.get()}", file=file)
    
    def get_default(self, index):
        line = ''
        with open('default.txt', 'r') as file:
            for _ in range(index+1):
                line = file.readline()
        return line.strip()
 
    def set_entry_text(self, entry, text):
        entry.delete(0, tk.END)
        entry.insert(0, text)
        return
 
    def make_entry(self, default):
        return tk.Entry(self.master, 
                    textvariable=tk.StringVar(self.master, value=default))
 
    def make_label(self, string):
        return tk.Label(self.master, text=string)
 
    def image(self):
        # Delete Live Camera
        if self.live_class is not None:
            self.live_class.delete()
        
        chip_type           = self.general_options[0].entry.get()
        objective           = self.general_options[1].entry.get()
        drug                = self.general_options[2].entry.get()
        folder              = self.entries[0].get() 
        concentration       = self.entries[2].get()                    
        index               = self.entries[3].get()                            
        bff                 = int(self.entries[4].get() )                              
        dap                 = int(self.entries[5].get() )                      
        gfp                 = int(self.entries[6].get() )       
        txr                 = int(self.entries[7].get() )       
        cy5                 = int(self.entries[8].get() )       
        focus_step          = int(self.entries[9].get() )           
        focus_total_range   = int(self.entries[10].get())        
        focus_point_range   = int(self.entries[11].get())            
        focus_x             = int(self.entries[12].get())        
        focus_y             = int(self.entries[13].get())        
        save_jpg            = self.entries[14].get()        
        alignment_model     = self.entries[15].get()        
        image_rotation      = int(self.entries[16].get())
        apart_per_img_x     = self.entries[17].get()
        apart_per_img_y     = self.entries[18].get()
        frame_width         = self.entries[19].get()
        frame_height        = self.entries[20].get()
        camera_pixel_width      = self.entries[21].get()
        camera_pixel_height     = self.entries[22].get()

        save_dir = (folder + '/' + time.strftime("%Y%m%d") + '/'+ concentration + 
                    '-' + self.unit_string.get() + '-' + drug + '/' + 'Chip'+ index + '/')
        # use the directories in save_dir to determine the number of times this 
        # chip has been imaged
        if not os.path.isdir(save_dir):
            time_point = 't00'
        else:
            points = len(next(os.walk(os.getcwd()))[1])
            time_point= "{0:0=2d}".format(points)
        save_dir = save_dir + time_point
        
        os.makedirs(save_dir, exist_ok=True)

        # Write info file
        self.write_info_file(save_dir)

        if chip_type == 'ML Chip':
            curr_chip = chip.ML_Chip()
        elif chip_type == 'KL Chip':
            curr_chip = chip.KL_Chip()
        
        if save_jpg == 'y' or save_jpg == 'Y':
            save_jpg = True
        else:
            save_jpg = False

        exp_names = ['BFF', 'DAP', 'GFP', 'TXR', 'CY5']
        exposures = []
        if self.bff_check.get():
            exposures.append(int(bff))
        else:
            exposures.append(False)
        if self.dap_check.get():
            exposures.append(int(dap))
        else:
            exposures.append(False)
        if self.gfp_check.get():
            exposures.append(int(gfp))
        else:
            exposures.append(False)
        if self.txr_check.get():
            exposures.append(int(txr))
        else:
            exposures.append(False)
        if self.cy5_check.get():
            exposures.append(int(cy5))
        else:
            exposures.append(False)

        first_through = True
        orginalx, orginaly, orginalz = pos.current(self.mmc)
        for i, exp in enumerate(exposures):

            if exp is not False and first_through:
                run.auto_image_chip(curr_chip,
                                    self.mmc,
                                    save_dir,
                                    index,
                                    alignment_model_name=alignment_model,
                                    naming_scheme=exp_names[i],
                                    focus_delta_z=focus_step,
                                    focus_total_z=focus_total_range,
                                    focus_next_point_range=focus_point_range,
                                    number_of_focus_points_x=focus_x,
                                    number_of_focus_points_y=focus_y,
                                    save_jpg=save_jpg,
                                    image_rotation=image_rotation,
                                    frame_width=frame_width,
                                    frame_height=frame_height,
                                    camera_pixel_width=camera_pixel_width,
                                    camera_pixel_height=camera_pixel_height,
                                    exposure=exp)
                first_through = False

            elif exp is not False:
                run.image_from_saved_positions(curr_chip, 
                                index, 
                                save_dir, 
                                self.mmc, 
                                realign=False, 
                                alignment_model_name=alignment_model,
                                naming_scheme=exp_names[i], 
                                save_jpg=save_jpg,
                                image_rotation=image_rotation,
                                frame_width=frame_width,
                                frame_height=frame_height,
                                camera_pixel_width=camera_pixel_width,
                                camera_pixel_height=camera_pixel_height,
                                exposure=exp)
        pos.set_pos(self.mmc, x=orginalx, y=orginaly, z=orginalz)
        
 
    def advanced(self):
        if self.advanced_visible:
            for i, label in enumerate(self.advanced_labels):
                label.grid_forget()
                self.entries[i+len(self.general_labels)-4].grid_forget()
            self.save_button.grid_forget()     
        else:
            # Layout the advanced options 
            for i, label in enumerate(self.advanced_labels):
                label.grid(row=i+len(self.general_labels)+2, column=0, columnspan=2)
                self.entries[i+len(self.general_labels)-4].grid(row=i+len(self.general_labels)+2, 
                                                                    column=2, columnspan=2)
            self.save_button.grid(row=i+len(self.general_labels)+3, column=2)
        self.advanced_visible = not self.advanced_visible
     
    def write_info_file(self, save_dir):
        with open(save_dir + '/info.txt', 'w+') as file:
            for i, val in enumerate(self.general_options):
                if i < 4:
                    print(f"{val.label}: {val.entry.get()}", file=file)
                else:
                    if val.label == 'Drug Concentration':
                        print(f"{val.label}: {self.entries[i-4].get()} {self.unit_string}", file=file)
                    else:
                        print(f"{val.label}: {self.entries[i-4].get()}", file=file)
            for val in self.advanced_options:
                i = i+1
                print(f"{val.label}: {self.entries[i-4].get()}", file=file)
       
 
def main():
    root = tk.Tk()
    ExpParmas(root)
    root.mainloop()
 
if __name__ == '__main__':
    main()