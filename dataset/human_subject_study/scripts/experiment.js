// customize the experiment by specifying a view order and a trial structure
exp.customize = function() {
    // record current date and time in global_data
    this.global_data.startDate = Date();
    this.global_data.startTime = Date.now();
    // specify view order
    this.views_seq = [
        intro,
        // botcaptcha,
        instructions,
        main,
        postTest,
        thanks
    ];

    // pick the description we'll display for each image-context pair
    // main_trials = _.shuffle(main_trials);
    main_trials_ident = _.shuffle(main_trials_ident);
    main_trials_nonident = _.shuffle(main_trials_nonident);
    selected_main_trials = _.shuffle(main_trials_ident.slice(0,1).concat(main_trials_nonident.slice(0,4)));
    
    console.log("selected_main_trials");
    console.log(selected_main_trials);

    // main_trials.splice(used_context_index, 1)

    // main_trials = selected_main_trials.concat(attention_checks);
    main_trials = selected_main_trials;
    this.trial_info.main_trials = _.shuffle(main_trials);
    console.log("main trials: ", this.trial_info.main_trials);

    // sample question order
    let questions = _.shuffle(["reconstructive", "image_fit", "all_relevant", "no_irrelevant", "added_info"]);
    console.log(questions)

    this.trial_info.q1 = questions[0];
    this.trial_info.q2 = questions[1];
    this.trial_info.q3 = questions[2];
    this.trial_info.q4 = questions[3];
    this.trial_info.q5 = questions[4];
    // console.log(this.trial_info.q1);
    // console.log(this.trial_info.q2);
    // console.log(this.trial_info.q3);

    // this.trial_info.first_notfitin_q = notfitin[0];
    // console.log(this.trial_info.first_notfitin_q);

    // adds progress bars to the views listed
    // view's name is the same as object's name
    this.progress_bar_in = ["main"];
    // this.progress_bar_in = ['practice', 'main'];
    // styles: chunks, separate or default
    this.progress_bar_style = "default";
    // the width of the progress bar or a single chunk
    this.progress_bar_width = 100;
};
