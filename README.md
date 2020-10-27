# pyAgriculture11783
This is a package to read TASKDATA.xml, TLG.xml and TLG.bin files in Python. 
The project is under development and feedback is apritiated!

The idea is to give a path to the xml/bin files and extract the data as pandas dataframes. The following code snipped is 
an example of how the data extraction are suppose to work. 

    from pandas import ExcelWriter
    py_agri = PyAgriculture('path/to/TaskData/')
    py_agri.gather_data()
    
    writer = ExcelWriter('PythonExport.xlsx')
    for i in range(len(py_agri.tasks)):
        if isinstance(py_agri.tasks[i], pd.DataFrame):
            py_agri.tasks[i].to_excel(writer, 'Sheet' + str(i))
    writer.save()