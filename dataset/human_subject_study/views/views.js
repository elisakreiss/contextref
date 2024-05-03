var botcaptcha = {
    name: "botcaptcha",
    title: "Language comprehension qualification",
    buttonText: "Continue to get a $6 bonus",
    render: function(){
        var viewTemplate = $("#botcaptcha-view").html();

        var story = "Images are pervasive across the Web -- they're embedded in news articles, tweets, and shopping websites but most of them are not accessible to people who rely on screen readers such as blind users. For instance, much less than 6% of all images on English-language Wikipedia have useful descriptions that would make them accessible. Recent work in computer science is trying to combat this issue.";

        var options = _.shuffle([{
            "response": "6% of all images are uploaded by English-language speaking users.",
            "truth": false
        }, {
            "response": "Wikipedia has the least amount of images compared to other popular websites.",
            "truth": false
        }, {
            "response": "image accessibility has been solved in recent years.",
            "truth": false
        }, {
            "response": "recent research is trying to figure out how to make images accessible.",
            "truth": true
        }, {
            "response": "blind people make up 6% of Wikipedia's daily users.",
            "truth": false
        }]);

        console.log("options[0]: ", options[0]["response"]);

        // var answer_id = 1;
        for (var answer_id in options) {
            console.log(answer_id);
            if (options[answer_id]["truth"]) {
                console.log("found", answer_id);
                break;
            } else {
                answer_id += 1
            }
        };

        $("#main").html(
            Mustache.render(viewTemplate, {
                name: this.name,
                title: this.title,
                text: story,
                question: "The passage points out that...",
                option1: options[0]["response"],
                option2: options[1]["response"],
                option3: options[2]["response"],
                option4: options[3]["response"],
                option5: options[4]["response"],
                button_response: "Submit",
                button: this.buttonText,
                button_finish: "Finish Experiment"
            })
        );

        // don't allow enter press in text field
        $('#listener-response').keypress(function(event) {
            if (event.keyCode == 13) {
                event.preventDefault();
            }
        });

        // don't show any error message
        $("#error").hide();
        $("#success").hide();

        $("#submit_response").on("click", function() {
            response = $('input[name=botresponse]:checked').val();
            console.log(response);
            console.log(parseInt(answer_id) + 1);

            // response correct
            if (response == (parseInt(answer_id) + 1)) {
                exp.global_data.botresponse = "correct: " + response;
                $("#submit_response").hide();
                $("#finish_exp").css({"display": "inline-block"});
                $("#next").css({"display": "inline-block"});
                $("#success").show();

            // response false
            } else {
                exp.global_data.botresponse = "false: " + response;
                $("#error").show();
                $("#finish_exp").css({"display": "inline-block"});
                $("#submit_response").hide();
            };
        });

        $("#next").on("click", function() {
            exp.global_data.continue = true;
            exp.findNextView();
        });

        $("#finish_exp").on("click", function() {
            exp.global_data.continue = false;
            exp.global_data.endTime = Date.now();
            exp.global_data.timeSpent =
                (exp.global_data.endTime - exp.global_data.startTime) / 60000;
            var trial_data = {
                trial_number: NaN,
                img_file: NaN,
                img_id: NaN,
                description: NaN,
                context: NaN,
                q1_type: NaN,
                q2_type: NaN,
                q3_type: NaN,
                q4_type: NaN,
                q5_type: NaN,
                q1_sliderval: NaN,
                q2_sliderval: NaN,
                q3_sliderval: NaN,
                q4_sliderval: NaN,
                q5_sliderval: NaN,
                discr_checkbox: NaN,
                mistake_checkbox: NaN,
                discr_comments: NaN,
                mistake_comments: NaN,
                rt_article_read_seconds: NaN,
                rt_qs_noimage_seconds: NaN,
                rt_qs_wimage_seconds: NaN,
                rt_trial: NaN
            };
            exp.trial_data.push(trial_data);
            exp.findPostTestView();
            // console.log(exp.costumize.views_seq);
        });

    },
    trials: 1
};

var intro = {
    name: "intro",
    // introduction title
    title: "Stanford NLP Group",
    // introduction text
    text:
        "Thank you for participating in our study!<br><br>In this study, you will see 5 short articles that contain an image. Each image will have a description associated with it in order to make the image accessible to users who can't see it. Your task will be to rate these descriptions by answering questions about them. The whole study should take no longer than <strong>10 minutes</strong>.<br><br>Please do <strong>not</strong> participate on a mobile device since the page won't display properly.<br><small>If you have any questions or concerns, don't hesitate to contact me at ekreiss@stanford.edu</small> ",
    legal_info:
        "<strong>LEGAL INFORMATION</strong>:<br><br>We invite you to participate in a research study on language production and comprehension.<br>Your experimenter will ask you to do a linguistic task such as reading sentences or words, naming pictures or describing scenes, making up sentences of your own, or participating in a simple language game.<br><br>You will be paid for your participation at the posted rate.<br><br>There are no risks or benefits of any kind involved in this study.<br><br>If you have read this form and have decided to participate in this experiment, please understand your participation is voluntary and you have the right to withdraw your consent or discontinue participation at any time without penalty or loss of benefits to which you are otherwise entitled. You have the right to refuse to do particular tasks. Your individual privacy will be maintained in all published and written data resulting from the study.<br>You may print this form for your records.<br><br>CONTACT INFORMATION:<br>If you have any questions, concerns or complaints about this research study, its procedures, risks and benefits, you should contact the Protocol Director Christopher Potts at <br>(650) 723-4284<br><br>If you are not satisfied with how this study is being conducted, or if you have any concerns, complaints, or general questions about the research or your rights as a participant, please contact the Stanford Institutional Review Board (IRB) to speak to someone independent of the research team at (650)-723-2480 or toll free at 1-866-680-2906. You can also write to the Stanford IRB, Stanford University, 3000 El Camino Real, Five Palo Alto Square, 4th Floor, Palo Alto, CA 94306 USA.<br><br>If you agree to participate, please proceed to the study tasks.",
    // introduction's slide proceeding button text
    buttonText: "Begin experiment",
    // render function renders the view
    render: function() {
        var viewTemplate = $("#intro-view").html();

        $("#main").html(
            Mustache.render(viewTemplate, {
                picture: "stimuli/stanford-nlp-logo.jpg",
                title: this.title,
                text: this.text,
                legal_info: this.legal_info,
                button: this.buttonText
            })
        );

        var prolificId = $("#prolific-id");
        var IDform = $("#prolific-id-form");
        var next = $("#next");

        var showNextBtn = function() {
            if (prolificId.val().trim() !== "") {
                next.removeClass("nodisplay");
            } else {
                next.addClass("nodisplay");
            }
        };

        if (config_deploy.deployMethod !== "Prolific") {
            IDform.addClass("nodisplay");
            next.removeClass("nodisplay");
        }

        prolificId.on("keyup", function() {
            showNextBtn();
        });

        prolificId.on("focus", function() {
            showNextBtn();
        });

        // moves to the next view
        next.on("click", function() {
            if (config_deploy.deployMethod === "Prolific") {
                exp.global_data.prolific_id = prolificId.val().trim();
            }

            exp.findNextView();
        });
    },
    // for how many trials should this view be repeated?
    trials: 1
};

var instructions = {
    name: "instructions",
    render: function(CT) {
        var viewTemplate = $("#instructions-view").html(); // don't think we even need mustache yet

        $("#main").html(
            Mustache.render(viewTemplate, {})
        );

        var next_button = $("#next");

        next_button.on('click', function () {
            exp.findNextView();
        });

    },
    trials: 1
};

var main = {
    name: "main",
    render: function(CT) {
        // fill variables in view-template
        console.log(exp.trial_info.main_trials[CT]);
        var viewTemplate = $("#main-view").html();

        let question_copy = {
            "reconstructive" : {
                "q": 'How well can you <strong>imagine</strong> this image in your mind?',
                "sl_left": 'Not well',
                "sl_right": 'Very well',
            },
            "image_fit" : {
                "q": 'How well do you understand <strong>why</strong> the <strong>image occurs in this article</strong>?',
                "sl_left": 'Not well',
                "sl_right": 'Very well',
            },
            "all_relevant" : {
                "q": 'How well does the description capture the <strong>relevant</strong> aspects of the image?',
                "sl_left": 'Not well',
                "sl_right": 'Very well',
            },
            "no_irrelevant" : {
                "q": 'Does the description mention <strong>extra information unnecessary</strong> for making the image accessible?',
                "sl_left": 'Yes, too much',
                "sl_right": 'No, not too much',
            },
            "added_info" : {
                "q": 'How much information does the description <strong>add to the caption/context paragraph</strong> that you couldn\'t have learned from the caption/context paragraph?',
                "sl_left": 'Adds nothing',
                "sl_right": 'Adds lots of info',
            }
        }

        let q_remainingqs = 'Do you have any <strong>remaining questions</strong> about the image?'
        let q_opencomment = 'Is there anything else you would like to <strong>add</strong>?'

        let img_id = exp.trial_info.main_trials[CT]['img_id'];
        let img_file = exp.trial_info.main_trials[CT]['image_url'];
        let img_path = 'stimuli/data/images/' + img_id;
        let description = exp.trial_info.main_trials[CT]['description'];
        let caption = exp.trial_info.main_trials[CT]['caption'];
        let article_title = exp.trial_info.main_trials[CT]['page_title'];
        let section_title = exp.trial_info.main_trials[CT]['section_title'];

        var section_context = exp.trial_info.main_trials[CT]['section_context'];
        var page_context = exp.trial_info.main_trials[CT]['page_context'];

        function shorten_text(text) {
            return(text.length > 1000 ? text.slice(0,1000)+" ..." : text)
        };

        if ((section_context != null) && (page_context != null)) {
            section_context = page_context.slice(0,200) == section_context.slice(0,200) ? null : shorten_text(section_context);
            page_context = shorten_text(page_context);
        };

        let mistake_checkbox_text = 'The description contains <strong>inaccurate</strong> information.';
        let discr_checkbox_text = 'The description contains possibly <strong>discriminatory language</strong>.';

        let q1 = question_copy[exp.trial_info.q1];
        let q2 = question_copy[exp.trial_info.q2];
        let q3 = question_copy[exp.trial_info.q3];
        let q4 = question_copy[exp.trial_info.q4];
        let q5 = question_copy[exp.trial_info.q5];

        question_copy[exp.trial_info.q1]['q_id'] = 'q1';
        question_copy[exp.trial_info.q2]['q_id'] = 'q2';
        question_copy[exp.trial_info.q3]['q_id'] = 'q3';
        question_copy[exp.trial_info.q4]['q_id'] = 'q4';
        question_copy[exp.trial_info.q4]['q_id'] = 'q5';

        console.log("question_copy: ", question_copy)

        console.log(section_context);
        console.log(page_context);
        console.log(section_context === page_context);
        console.log(section_context == page_context);
        console.log("Condition: ", exp.trial_info.main_trials[CT]['heuristic_category']);

        // != null ? exp.trial_info.main_trials[CT]['section_context'].slice(0,1000) : null


        $("#main").html(
            Mustache.render(viewTemplate, {
                article_title: article_title,
                section_title: section_title,
                article_text: page_context,
                section_context: section_context,
                critical_text: description,
                caption_text: caption,
                picture: img_path,
                q1: q1['q'],
                q1_slider_left: q1['sl_left'],
                q1_slider_right: q1['sl_right'],
                q2: q2['q'],
                q2_slider_left: q2['sl_left'],
                q2_slider_right: q2['sl_right'],
                q3: q3['q'],
                q3_slider_left: q3['sl_left'],
                q3_slider_right: q3['sl_right'],
                q4: q4['q'],
                q4_slider_left: q4['sl_left'],
                q4_slider_right: q4['sl_right'],
                q5: q5['q'],
                q5_slider_left: q5['sl_left'],
                q5_slider_right: q5['sl_right'],
                q6: "How good is the description for <strong>overall</strong> nonvisual accessibility?",
                q6_slider_left: "Not good",
                q6_slider_right: "Very good",
                q_remainingqs: q_remainingqs,
                q_opencomment: q_opencomment,
                discr_checkbox: discr_checkbox_text,
                mistake_checkbox: mistake_checkbox_text
            })
        );

        window.scrollTo(0,0);

        // states of the annotation
        var STATES = {
            READ: 0,
            RESPOND: 1
        };
        var state = STATES.READ;

        // objects
        var instruction = $("#instruction");
        var respond_area = $('#questions');
        var comment_area = $('#comments');
        var picture = $('#picture');
        var img_descr_box = $('#img_descr_box');
        var alt_text = $('#alt_text');
        var reminder_text = $('#reminder_text');
        var remainingqs = $('#remainingqs');
        var remainingqs_text = $('#remainingqs_text');
        var error = $('#error');
        var show_img = $('#show_img');
        var next = $('#next');
        var discr_checkbox = $('#discr_checkbox');
        var mistake_checkbox = $('#mistake_checkbox');
        var discr_box = $('#discr_box');
        var mistake_box = $('#mistake_box');
        var mistake_comments = $('#mistake_comments');
        var discr_comments = $('#discr_comments');
        var mistake_comments_text = $('#mistake_comments_text');
        var discr_comments_text = $('#discr_comments_text');
        var open_comments_text = $('#open_comments_text');
        var rt_article_read = 0;
        var rt_qs_noimage = 0;
        var rt_qs_wimage = 0;

        var q1_sliderval = [0]
        var q2_sliderval = [0]
        var q3_sliderval = [0]
        var q4_sliderval = [0]
        var q5_sliderval = [0]

        // functions
        function remove_reconstr_q(q_id) {
            if (q_id == 'q1') {
                $(".labels1").css({"opacity": 0.3});
                $("#question1").css({"opacity": 0.3});
                $("input[name='slider1']").attr("disabled","disabled");
                $("#prev_sel1").text("");
                $('input[name=slider2]').prop('checked', false);
                $('input[name=slider3]').prop('checked', false);
                $('input[name=slider4]').prop('checked', false);
                $('input[name=slider5]').prop('checked', false);
            } else if (q_id == 'q2') {
                $(".labels2").css({"opacity": 0.3});
                $("#question2").css({"opacity": 0.3});
                $("input[name='slider2']").attr("disabled","disabled");
                $("#prev_sel2").text("");
                $('input[name=slider1]').prop('checked', false);
                $('input[name=slider3]').prop('checked', false);
                $('input[name=slider4]').prop('checked', false);
                $('input[name=slider5]').prop('checked', false);
            } else if (q_id == 'q3') {
                $(".labels3").css({"opacity": 0.3});
                $("#question3").css({"opacity": 0.3});
                $("input[name='slider3']").attr("disabled","disabled");
                $("#prev_sel3").text("");
                $('input[name=slider1]').prop('checked', false);
                $('input[name=slider2]').prop('checked', false);
                $('input[name=slider4]').prop('checked', false);
                $('input[name=slider5]').prop('checked', false);
            } else if (q_id == 'q4') {
                $(".labels4").css({"opacity": 0.3});
                $("#question4").css({"opacity": 0.3});
                $("input[name='slider4']").attr("disabled","disabled");
                $("#prev_sel4").text("");
                $('input[name=slider1]').prop('checked', false);
                $('input[name=slider2]').prop('checked', false);
                $('input[name=slider3]').prop('checked', false);
                $('input[name=slider5]').prop('checked', false);
            } else if (q_id == 'q5') {
                $(".labels5").css({"opacity": 0.3});
                $("#question5").css({"opacity": 0.3});
                $("input[name='slider5']").attr("disabled","disabled");
                $("#prev_sel5").text("");
                $('input[name=slider1]').prop('checked', false);
                $('input[name=slider2]').prop('checked', false);
                $('input[name=slider3]').prop('checked', false);
                $('input[name=slider4]').prop('checked', false);
            } else {
                console.log("ERROR: q_id unknown");
            };
        };

        function responses_complete() {
            return($('input[name=slider1]:checked').val() > 0 & 
            $('input[name=slider2]:checked').val() > 0 & 
            $('input[name=slider3]:checked').val() > 0 & 
            $('input[name=slider4]:checked').val() > 0 & 
            $('input[name=slider5]:checked').val() > 0& 
            $('input[name=slider6]:checked').val() > 0)
        };

        // event functions
        var update_page = () => {
            // when input is selected, response and additional info stored in exp.trial_info
            if (state == STATES.READ) {
                state = STATES.RESPOND;
                respond_area.css({"display" : "inline"});
                alt_text.css({"opacity": "1"});
                comment_area.css({"display" : "inline"});
                show_img.css({"display" : "block"});
                instruction.text("Now answer the questions below!");
                next.text("Continue!");
                next.css({"display": "none"});
                rt_article_read = Date.now();
            }
            else {
                if (responses_complete()) {
                    rt_qs_wimage = Date.now(); // measure RT before anything else
                    q1_sliderval.push($('input[name=slider1]:checked').val())
                    q2_sliderval.push($('input[name=slider2]:checked').val())
                    q3_sliderval.push($('input[name=slider3]:checked').val())
                    q4_sliderval.push($('input[name=slider4]:checked').val())
                    q5_sliderval.push($('input[name=slider5]:checked').val())
                    q6_sliderval.push($('input[name=slider6]:checked').val())

                    var trial_data = {
                        trial_number: CT + 1,
                        img_file: img_file,
                        img_id: img_id,
                        description: description,
                        caption: caption,
                        page_context: page_context,
                        page_title: article_title,
                        section_context: section_context,
                        section_title: section_title,
                        q1_type: exp.trial_info.q1,
                        q2_type: exp.trial_info.q2,
                        q3_type: exp.trial_info.q3,
                        q4_type: exp.trial_info.q4,
                        q5_type: exp.trial_info.q5,
                        q6_type: "overall",
                        q1_sliderval: q1_sliderval,
                        q2_sliderval: q2_sliderval,
                        q3_sliderval: q3_sliderval,
                        q4_sliderval: q4_sliderval,
                        q5_sliderval: q5_sliderval,
                        q6_sliderval: q6_sliderval,
                        discr_checkbox: discr_checkbox.prop('checked'),
                        mistake_checkbox: mistake_checkbox.prop('checked'),
                        discr_comments: discr_comments_text.val().trim(),
                        mistake_comments: mistake_comments_text.val().trim(),
                        open_comments: open_comments_text.val(),
                        rt_article_read_seconds: (rt_article_read - startingTime) / 1000,
                        rt_qs_noimage_seconds: (rt_qs_noimage - rt_article_read) / 1000,
                        rt_qs_wimage_seconds: (rt_qs_wimage - rt_qs_noimage) / 1000,
                        rt_trial: (rt_qs_wimage - startingTime) /1000
                    };
                    exp.trial_data.push(trial_data);
                    exp.findNextView();
                } else {
                    console.log(error);    
                    error.css({"display": "block"});
                };
            }
        }

        // events
        discr_checkbox.change(function() {
            if (this.checked) {
                discr_comments.css({'display' : 'block'});
            } else {
                discr_comments.css({'display' : 'none'});
            }
        });
        mistake_checkbox.change(function() {
            if (this.checked) {
                mistake_comments.css({'display' : 'block'});
            } else {
                mistake_comments.css({'display' : 'none'});
            }
        });

        show_img.on("click", function(){
            console.log('clicked button');
            if (responses_complete()) {
                rt_qs_noimage = Date.now();
                reminder_text.css({opacity: "1"});
                img_descr_box.css({display: "none"});
                // prepare next screen
                var q1_resp = $('input[name=slider1]:checked').val();
                var q2_resp = $('input[name=slider2]:checked').val();
                var q3_resp = $('input[name=slider3]:checked').val();
                var q4_resp = $('input[name=slider4]:checked').val();
                var q5_resp = $('input[name=slider5]:checked').val();
                var q6_resp = $('input[name=slider6]:checked').val();
                $("#prev_sel1").text("|  Previous selection: " + q1_resp.toString() + "/5");
                $("#prev_sel2").text("|  Previous selection: " + q2_resp.toString() + "/5");
                $("#prev_sel3").text("|  Previous selection: " + q3_resp.toString() + "/5");
                $("#prev_sel4").text("|  Previous selection: " + q4_resp.toString() + "/5");
                $("#prev_sel5").text("|  Previous selection: " + q5_resp.toString() + "/5");
                $("#prev_sel6").text("|  Previous selection: " + q6_resp.toString() + "/5");

                remove_reconstr_q(q_id=question_copy['reconstructive']['q_id']);
                $('input[name=slider6]').prop('checked', false);
                remainingqs.css({'opacity' : 0.3});
                remainingqs_text.prop('disabled', true);
                show_img.css({'display' : 'none'});
                error.css({"display": "none"});

                picture.css({'display' : 'block'});
                discr_box.css({'display' : 'block'});
                mistake_box.css({'display' : 'block'});
                next.css({"display": "block"});

                window.scrollTo(0,0);

                // record data
                q1_sliderval = [q1_resp];
                q2_sliderval = [q2_resp];
                q3_sliderval = [q3_resp];
                q4_sliderval = [q4_resp];
                q5_sliderval = [q5_resp];
                q6_sliderval = [q6_resp];
            } else {
                console.log(error);    
                error.css({"display": "block"});
            };
        });
        
        next.on("click", update_page);

        // record trial starting time
        var startingTime = Date.now();
    },
    trials: 5
};

var postTest = {
    name: "postTest",
    title: "Additional Info",
    text:
        "Answering the following questions is optional, but will help us understand your answers.",
    buttonText: "Continue",
    render: function() {
        var viewTemplate = $("#post-test-view").html();
        $("#main").html(
            Mustache.render(viewTemplate, {
                title: this.title,
                text: this.text,
                buttonText: this.buttonText
            })
        );

        $("#next").on("click", function(e) {
            // prevents the form from submitting
            e.preventDefault();

            // records the post test info
            exp.global_data.HitCorrect = $("#HitCorrect").val();
            exp.global_data.age = $("#age").val();
            // exp.global_data.education = $("#education").val();
            exp.global_data.languages = $("#languages").val();
            exp.global_data.enjoyment = $("#enjoyment").val();
            exp.global_data.comments = $("#comments")
                .val()
                .trim();
            // exp.global_data.difficulties = $("#difficulties")
            //     .val()
            //     .trim();
            exp.global_data.endTime = Date.now();
            exp.global_data.timeSpent =
                (exp.global_data.endTime - exp.global_data.startTime) / 60000;

            // moves to the next view
            exp.findNextView();
        });
    },
    trials: 1
};

var thanks = {
    name: "thanks",
    message: "Thank you for taking part in this experiment!",
    render: function() {
        var viewTemplate = $("#thanks-view").html();

        // what is seen on the screen depends on the used deploy method
        //    normally, you do not need to modify this
        if (
            config_deploy.is_MTurk ||
            config_deploy.deployMethod === "directLink"
        ) {
            // updates the fields in the hidden form with info for the MTurk's server
            $("#main").html(
                Mustache.render(viewTemplate, {
                    thanksMessage: this.message
                })
            );
        } else if (config_deploy.deployMethod === "Prolific") {
            $("main").html(
                Mustache.render(viewTemplate, {
                    thanksMessage: this.message,
                    extraMessage:
                        "Please press the button below to confirm that you completed the experiment with Prolific. Your completion code is C6F01LDX.<br />" +
                        "<a href=" +
                        config_deploy.prolificURL +
                        ' class="prolific-url">Confirm</a>'
                })
            );
        } else if (config_deploy.deployMethod === "debug") {
            $("main").html(Mustache.render(viewTemplate, {}));
        } else {
            console.log("no such config_deploy.deployMethod");
        }

        exp.submit();
    },
    trials: 1
};
