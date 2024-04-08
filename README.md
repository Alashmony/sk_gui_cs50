# Pandas Playground

#### Video Demo:  Here is a link to the project's [video](https://cs50-vid.alashmony.site/) or on [YouTube](https://youtu.be/kbME6EuDnwg).
The first 3 minuted is a description, the remaining 4 minutes are a Demo.

# The project started as the final project for CS50

#### Description:

To teach or show case pandas functions to students without the need to ask them to install python or prepare an environment

Project is deployed on [Render](https://render.com/) and you can check it via [Alashmony.site](https://pandas.alashmony.site).

No database is used as a free tiers of cloud will be used with many limitations. This version is a show case / demo only.

## Current capabilities:

- Upload a dataset with "CSV", "XLS", or "XLSX" formats, no size limits yet:
    - *Future versions should require a login before uploading any datasets and should support more types.*
    - Once a file was choosen, the application checks its extension, if the extension is not supported, an error message will appear.
    - If the files is in a supported format, it will be stored in a file on a server inside a folder similar to a session uniquie ID, a UUID 4
    - Then, the file is being red by pandas and stored in a dataframe (df).
    - *In future versions, the files should be removed and data will be stored in a database.*
    - The very first dataframe is stored in a session variable (df) as a dictonary with "v0" as the key and the dataframe as the value, this version is never touched/changed.
    - *In the future implememtation, this dataframe should be stored in a table and linked to the user uploaded it.*
- Generate a data exploration report (EDA) from [ydata-profiling](https://github.com/ydataai/ydata-profiling):
    - This step takes time as the report will be generated within a while.
    - Once the report is generated, using BeatuifulSoup, the application removes the Navigation bar from the report to avoid overwriting the app Navigation bar.
    - The report Navigation bar is not needed, it contains anchors to the page headers only.
- Create data manipulation steps with a GUI to show the output step-by-step:
    - The app reads all methods that are applicable to a DataFrame object automatically and its documentations.
    - The app also reads the columns for the final version of the dataframe, if the return value of the last step is not a dataframe, it will generate column names for the very first version.
    - *In future versions, the app should go back step-by-step to get the columns for latest version of the dataframe.*
    - Using JavaScript, You can choose the method you would like to use to manipulate the data, the documentation will directly appear. You can change the args manually or add column names from the select list.
    - If the "inplace" arg is used at any time, it will be automatically removed, You should not change the current version of the dataframe.
- Remove steps and get back to the very first version "version 0" which is the uploaded dataset:
    - When you did not specify a step to remove, The "Remove step" button will "Remove all steps" as it will be shown on its title.
    - This removes all steps stores in the session, also, it removes all versions of the dataframe **Except for "v0"**.
    - *After adding the database, this should remove only steps, the dataframe will not be stored except for version0.*
- Test the ability to remove a step within the steps and if applicable, it will be removed and other steps will be applied to the data:
    - When you specify a step to remove, the application will check if this is a valid step in the stored steps. If it is not found, an error appears.
    - If the step is found, the application will try to apply all other steps in order without this step. If it is not applicable, an error will appear.
    - If the steps can be applied after removing this one, the application will replace the old steps (Showing that one of them is removed), and the new dataframe versions to replace the old ones.

## Future enhancements:

- Limit the file size.
- Add the registration / login functionalities.
- Create data tables for each project and link version 0 of the data and steps to the username.
- Enable users to get back to their projects using the data stored.
- The uploaded files and the raw report will be removed automatically.
- Add manipulation steps on the column aka numpy.Series / pandas.Series level.
- Add the ability to have multiple dataframes in the same project.
- Enable plotting data within the application.
- Add SkiKit-Learn to run ML experiments online.

**Notes:**

* the uploaded data, the uploaded file, and the steps you applied is related to your current session, you cannot get back to them.
* The uploaded files are only removed manually from the server, will be changed in future updated to automatic removals
* No login required
