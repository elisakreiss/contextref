var config_deploy = {

    // OBLIGATORY FIELDS

    // the experimentID is needed to recover data from the _babe server app
    // you receive the experimentID when you create the experiment using the _babe server app
    // "experimentID": "100",
    // // if you use the _babe server app, specify its URL here
    "experimentID": "pilot-study-experiment.json",
    // "serverAppURL": "https://example-project-july2022-default-rtdb.firebaseio.com/",

    // set deployment method; use one of:
    //'debug', 'localServer', 'MTurk', 
    // 'MTurkSandbox', 'Prolific', 'directLink'
    "deployMethod": "debug",
    // "deployMethod": "directLink",
    // "deployMethod": "Prolific",
    // "deployMethod": "MTurk",
    // "deployMethod": "MTurkSandbox",

    // who to contact in case of trouble
    "contact_email": "ekreiss@stanford.edu",

    // OPTIONAL FIELDS

    // set the prolific completion URL if the deploy method is "Prolific"
    // the URL should look something like this - https://app.prolific.ac/submissions/complete?cc=ABCD1234
    "prolificURL": "https://app.prolific.co/submissions/complete?cc=C6F01LDX"
};