# Pandas Playground

#### Video Demo:  Here is a link to the project's [video](https://cs50-vid.alashmony.site/).

# The project started as the final project for CS50

#### Description:

To teach or show case pandas functions to students without the need to ask them to install python or prepare an environment

Project is deployed on [Render](https://render.com/) and you can check it via [Alashmony.site](https://pandas.alashmony.site).

## Current capabilities:

- Upload a dataset with "CSV", "XLS", or "XLSX" formats, no size limits yet.
- Generate a data exploration report (EDA) from [ydata-profiling](https://github.com/ydataai/ydata-profiling) .
- Create data manipulation steps with a GUI to show the output step-by-step.
- Remove steps and get back to the very first version "version 0" which is the uploaded dataset.
- Test the ability to remove a step within the steps and if applicable, it will be removed and other steps will be applied to the data.


## Future enhancements:

- Limit the file size.
- Add the registration / login functionalities.
- Create data tables for each project and link version 0 of the data and steps to the username.
- Enable users to get back to their projects using the data stored. 
- The uploaded files will be removed automatically.
- Add manipulation steps on the column level
- Add the ability to have multiple dataframes in the same project.
- Enable plotting data within the application.
- Add SkiKit-Learn to run ML experiments online

**Notes:**

* the uploaded data, the uploaded file, and the steps you applied is related to your current session, you cannot get back to them.
* The uploaded files are only removed manually from the server, will be changed in future updated to automatic removals
* No login required