import tkinter as tk 
from tkinter import ttk 

class TreeviewEdit(ttk.Treeview):
    def __init__(self, master, **kw):
        super().__init__(master, **kw)
    
        self.bind("<Double-1>", self.on_double_click)
    
    def on_double_click(self,event):
        #event is mouse corner
        #identify the region that was double-clicked
        region_clicked = self.identify_region(event.x, event.y) #define the are we clicked
        if region_clicked not in ('tree','cell'):
            return 

        #which item was double-clicked, for ex: "#0" is the first column, followed by "#1", etc
        column = self.identify_column(event.x)

        #for example: "#0" will be -1
        column_index = int(column[1:]) - 1

        #for example: 001
        selected_id = self.focus()

        #this will contain both text and values from the given item id
        selected_values = self.item(selected_id)
        
        if column == "#0":
            selected_text = selected_values.get('text')
        else:
            selected_text = selected_values.get('values')[column_index]
        
        column_box = self.bbox(selected_id, column) #return x,y position. width, height

        #create new entry
        entry_edit = ttk.Entry(self.master,width=column_box[2])

        #record the column indx and item id 
        entry_edit.editing_column_index = column_index
        entry_edit.editing_item_id = selected_id

        entry_edit.insert(0,selected_text)
        entry_edit.select_range(0,tk.END)

        entry_edit.focus()

        entry_edit.bind("<FocusOut>", self.on_focus_out)
        entry_edit.bind("<Return>", self.on_enter_pressed)

        entry_edit.place(x = column_box[0],
                         y = column_box[1],
                         w = column_box[2],
                         h = column_box[3])
        
    def on_enter_pressed(self,event):
        new_text = event.widget.get()
        selected_id = event.widget.editing_item_id
        column_index = event.widget.editing_column_index
        if column_index == -1:
            self.item(selected_id, text = new_text)
        else:
            current_values = self.item(selected_id).get('values')
            current_values[column_index] = new_text
            self.item(selected_id, values=current_values)
        event.widget.destroy()


    def on_focus_out(self,event):
        event.widget.destroy()


if __name__ == '__main__':
    root = tk.Tk()
    column_names = ('vehicle_name', 'year', 'color')
    treeview_vehicles = TreeviewEdit(root, columns = column_names)
   
    
    treeview_vehicles.heading('#0', text = "Vehicle Type")
    treeview_vehicles.heading('vehicle_name', text = "Vehicle Name")
    treeview_vehicles.heading('year', text = "Year")
    treeview_vehicles.heading('color', text='Color')

    #define the main row
    sedan_row = treeview_vehicles.insert(parent='',index=tk.END,text = 'Sedan')

    #insert the subrow for main row 
    treeview_vehicles.insert(parent=sedan_row, index=tk.END, values=('Nissan', '2010', 'Silver'))
    treeview_vehicles.insert(parent=sedan_row, index=tk.END, values=('Toyota', '2012', 'Blue'))

    treeview_vehicles.pack(fill = tk.BOTH, expand=True)

    root.mainloop()
