# Losebot
## A means to download food & exercise logs from loseit.com 

The Loseit® app and website provide a way to track what you eat each day, and any exercise.

On the loseit.com website, you can log in and browse your entries by day or week. 
You can also export log data for a single week under _Insights > Weekly Summary > Export to spreadsheet_
 
However, there is no way to download more than a week at once -- you have to download your data by manually clicking through many times. 
Furthermore, to keep your records up to date, you need to come back to the site and pick up where you last left off.

Enter losebot!

Losebot offers to download all your data from the beginning of your entries,
and stores the downloaded data into a folder (named "downloaded_loseit_food_exercise"). When you run it a second time, it checks that folder and downloads
only newer data.

## How to run the program

The program requires python version 3+, which on a mac you can install with `brew install python3` (assuming `homebrew` already installed). For a more automated approach, use `direnv`, for which a dotfile already exists.

It also requires the [selenium](https://pypi.org/project/selenium/) to support stateful web browsing, which allows losebot to log into your loseit account. The command to install selenium is:

`python setup.py install` or manually via `pip install selenium`

The command to run losebot is:

`python losebot.py`

The program will prompt you for your username, password, and the date to start downloading from. 
(The default start date is set to one year ago.) Once you've downloaded some data, the next time
you run it, losebot won't prompt you for a date because it knows where it left off.

## Advanced properties

Although losebot will prompt you for your login, you may wish to create a properties 
file so that you can rerun losebot more easily. 
The format for the properties file is in the format like this example:

```properties
[Losebot]
username=myemail@someserver.com
password=mysecretpassword
```

and to use a properties file, invoke losebot supplying the path to your properties file as the first argument, like so: 

`python losebot.py <my properties file>`

## Debugging problems

### When chrome changes

The chrome webdriver will update automatically, and its options and behavior change over time. For example, the option for "--headless" changed to "--headless=new"
### When loseit changes their web site

Log into losit.com, navigate to insights -> weekly summary

Use the browser's developer mode to see the javascript files that are downloaded by the browser. 

Search in each for "export".
