# the app

mntr is a page monitor app.

the user adds links to it, and it checks each of them to see if they changed in the meanwhile. if the page has changed, it notifies the user.

for each monitored page, the user can select the frequency to check for changes: [number][unit]; for example: 3min, 1day, 7month, etc. 

when the app detects a change it notifies the user, using mail, slack, telegram. the user can visit the settings page to chose how to receive the notification and configure the selected service.

the content of the notification should include a diff visualizing the added/removed content.

in the main ui, the user should see a list of the monitored pages, as well as the checking frequency, time since last check. 

the pages that changed since the last time the user consulted the diff should be visually disctintive. 

when clicking these page, the user can see the diff of the change.
