""" Test Q+A. """

from asl_rulebook2.webapp.tests.utils import init_webapp, \
    check_sr_filters, find_child, find_children, wait_for_elem, get_image_filename, unload_elem, unload_sr_text
from asl_rulebook2.webapp.tests.test_search import do_search

# ---------------------------------------------------------------------

def test_full_qa_entry( webapp, webdriver ):
    """Test handling of a Q+A entry that has everything."""

    # initialize
    webapp.control_tests.set_data_dir( "qa" )
    init_webapp( webapp, webdriver )
    check_sr_filters( [ "index", "qa" ] )

    # bring up the Q+A entry
    results = do_search( "full" )

    # NOTE: Because the first search result has a ruleid of F1, any Q+A that reference F1
    # will auto-show in the rule info popup.
    qa_entry = _unload_rule_info_qa()
    expected = {
        "caption": "F1",
        "content": [ {
            "question": "This is a full question about something [EXC: those other things].",
            "icon": "question.png",
            "image": "thought-bubble.png",
            "answers": [
                [ "On the one hand, it could be this.", "Perry Sez" ],
                [ "But alternatively, it could be that.", "Perry Sez" ],
            ],
            "see_other": "See other errata: Your guru."
        }, {
            "question": "As a follow-up, what is the meaning of life?",
            "icon": "question.png",
            "answers": [
                [ "It is what you make of it [EXC: See above].", "_unknown_" ]
            ]
        } ]
    }
    assert qa_entry == expected

    # check the same Q+A entry in the search results
    find_child( ".close-rule-info" ).click()
    expected["content"][0]["question"] = expected["content"][0]["question"].replace( "full", "((full))" )
    result = results[1]
    del result[ "sr_type" ]
    assert result == expected

# ---------------------------------------------------------------------

def test_info_qa_entry( webapp, webdriver ):
    """Test handling of an informational Q+A entry."""

    # initialize
    webapp.control_tests.set_data_dir( "qa" )
    init_webapp( webapp, webdriver )

    # bring up the Q+A entry
    do_search( "information" )

    # check the Q_A entry in the rule info popup
    qa_entry = _unload_rule_info_qa()
    expected = {
        "caption": "I1",
        "content": [ {
            "icon": "info.png",
            "source": "GameSquad",
            "info": [
                "This Q+A has no question, just answers.",
                "And another one"
            ],
        }, {
            "icon": "info.png",
            "source": "GameSquad",
            "info": [ "And yet another one" ],
        } ]
    }
    assert qa_entry == expected

# ---------------------------------------------------------------------

def test_missing_content( webapp, webdriver ):
    """Test handling of a Q+A entry that has no content."""

    # initialize
    webapp.control_tests.set_data_dir( "qa" )
    init_webapp( webapp, webdriver )

    # bring up the Q+A entry
    results = do_search( "missing" )

    # check the Q+A entry in the search results
    # NOTE: Q+A captions are ignored by the search engine (since they usually just contain just ruleid's),
    # so search terms are *not* highlighted.
    expected = {
        "caption": "Missing content",
    }
    assert len(results) == 1
    result = results[0]
    del result[ "sr_type" ]
    assert result == expected

# ---------------------------------------------------------------------

def test_missing_answer( webapp, webdriver ):
    """Test handling of a Q+A entry that has a question but no answers."""

    # initialize
    webapp.control_tests.set_data_dir( "qa" )
    init_webapp( webapp, webdriver )

    # bring up the Q+A entry
    results = do_search( "unanswerable" )

    # check the Q+A entry in the search results
    expected = {
        "caption": "N1",
        "content": [ {
            "question": "An ((unanswerable)) question.",
            "icon": "question.png",
        } ]
    }
    assert len(results) == 1
    result = results[0]
    del result[ "sr_type" ]
    assert result == expected

# ---------------------------------------------------------------------

def unload_qa( qa_elem ):
    """Unload a Q+A entry from the UI."""

    # initialize
    qa_entry = {}

    # unload the top-level fields
    unload_elem( qa_entry, "caption", find_child(".caption",qa_elem), adjust_hilites=True )

    # unload each content node
    qa_content = []
    for content_elem in find_children( ".content", qa_elem ):

        # unload the top-level fields
        content = {
            "icon": get_image_filename( find_child( "img.icon", content_elem ) ),
        }
        unload_elem( content, "question", find_child(".question",content_elem), adjust_hilites=True )
        unload_elem( content, "image", find_child("img.imageZoom",content_elem) )
        unload_elem( content, "see_other", find_child(".see-other",content_elem), adjust_hilites=True )

        # unload the answers (if any)
        answers = []
        for answer_elem in find_children( ".answer", content_elem ):
            answers.append( [
                unload_sr_text( answer_elem ),
                find_child( "img.icon", answer_elem ).get_attribute( "title" ),
            ] )
        if answers:
            content["answers"] = answers

        # unload the info (if any)
        info = [
            c.text for c in find_children( ".info", content_elem )
        ]
        if info:
            content["info"] = info
            content["source"] = find_child( "img.icon", content_elem ).get_attribute( "title" )

        # save the content node
        qa_content.append( content )

    # save the content nodes (if any)
    if qa_content:
        qa_entry["content"] = qa_content

    return qa_entry

def _unload_rule_info_qa():
    """Unload a Q+A entry from the rule info popup."""
    popup = wait_for_elem( 2, "#rule-info" )
    assert popup
    elems = find_children( ".qa", popup )
    assert len(elems) == 1 # nb: we assume there's only 1 Q+A entry
    return unload_qa( elems[0] )
