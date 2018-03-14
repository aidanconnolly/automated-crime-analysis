# Automated outlier detection in crime using programming 

This project was completed in partial fulfillment of the requirements for a degree with honors at the University of Nebraska-Lincoln.

# Abstract
After the University of Nebraska-Lincoln Police department began publishing their Daily Crime and Fire Log online, journalists and other members of the public have been able to view updates almost instantly. They can see what incidents have been reported so far for that day, and they can view any day back to 2005. Using an advanced search, they can also filter the data by date range, location or crime type.  

However, there is no way to analyze the data. There's no way to see how crime reports have evolved over time. Other people have developed programs to look at past trends and outliers to see how things have changed, but there was no way to know when new outliers were happening. The goal of this program is to fill that gap.

This program uses Python to calculate the average number of reports per month for each crime type. Then, as the reports come in each month, it checks to see if any crime type has an abnormally high number of crimes reported. At the end of the month, it checks to see if an unusually low number of crimes were reported for a crime type.

If an abnormality is found, a message is created and sent to a messaging platform common to newsrooms called Slack. This allows journalists to be notified of the abnormality. From there, they're able to look into the reports to determine if it is worth a story.


