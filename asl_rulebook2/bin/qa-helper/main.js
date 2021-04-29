var gQuestionImageUrl = "../../webapp/static/images/question.png" ;
var gAnswerImageUrl = "../../webapp/static/images/answer.png" ;

// --------------------------------------------------------------------

$(document).ready( function() {

    // initialize
    $( "input.rules" ).on( "change keyup paste", updatePreviews ) ;

    // initialize
    $( "button#copy-json" ).on( "click", function() {
        window.getSelection().selectAllChildren( document.getElementById( "json-preview" ) ) ;
        document.execCommand( "copy" ) ;
        window.getSelection().removeAllRanges() ;
    } ) ;

    // initialize
    $( "button#add-qa" ).on( "click", addQA ) ;
    addQA() ;

    // initialize
    $(window).on( "resize", resizeQA ) ;

    // reset
    $( "input.rules" ).val( "" ).focus() ;
    $( "textarea" ).val( "" ) ;
} ) ;

// --------------------------------------------------------------------

function addQA()
{
    function addText( $elem, text ) {
        $elem.insertAtCaret( text ) ;
    }

    // resize the existing Q+A
    $( "textarea.question" ).css( "height", "2em" ) ;
    $( "textarea.answer" ).css( "height", "2em" ) ;

    // add the new Q+A
    var $qa = $( [ "<div class='qa'>",
        "<b>Question:</b>", "<textarea class='question'></textarea>",
        "<b>Answer:</b>", "<textarea class='answer'></textarea>",
        "</div>"
    ].join( "" ) ) ;
    $qa.on( "change keyup paste", updatePreviews ) ;
    $qa.find( "textarea" ).on( "focus", function() {
        $(this).select() ;
    } ) ;
    $qa.find( "textarea.answer" ).on( "keydown", function( evt ) {
        if ( evt.ctrlKey && evt.key == "x" ) {
            addText( $(this), "Yes. " ) ;
            evt.preventDefault() ;
        } else if ( evt.ctrlKey && evt.key == "c" ) {
            addText( $(this), "No. " ) ;
            evt.preventDefault() ;
        }
    } ) ;
    $qa.find( "textarea" ).on( "keydown", function( evt ) {
        if ( evt.ctrlKey && evt.key == "p" ) {
            addText( $(this), "<p> " ) ;
            evt.preventDefault() ;
        } else if ( evt.ctrlKey && evt.key == "i" ) {
            var selText = $(this).val().substring( $(this)[0].selectionStart, $(this)[0].selectionEnd ) ;
            addText( $(this), "<em>"+selText+"</em>" ) ;
            evt.preventDefault() ;
        } else if ( evt.ctrlKey && evt.key == "e" ) {
            var selText = $(this).val().substring( $(this)[0].selectionStart, $(this)[0].selectionEnd ) ;
            addText( $(this), "<q>"+selText+"</q>" ) ;
            evt.preventDefault() ;
        }
    } ) ;
    $( "#qa" ).append( $qa ) ;
    resizeQA() ;
    updatePreviews() ;
    $qa.find( ".question" ).focus() ;
}

function resizeQA()
{
    var $jsonPreview = $( "#json-preview" ) ;
    var yBottom = $jsonPreview.position().top + $jsonPreview.height() ;
    var $qa = $( "#qa" ) ;
    var newHeight = yBottom - $qa.position().top + 4 ;
    $qa.height( newHeight ) ;
}

// --------------------------------------------------------------------

function updatePreviews()
{
    function extractRuleIds( val ) {
        var ruleids = [] ;
        val = val.replace( /&/g, "," ) ;
        for ( var ruleid of val.split( "," ) ) {
            ruleid = ruleid.trim() ;
            if ( ! ruleid.match( /^[A-Z][0-9.]+$/ ) )
                continue ;
            ruleids.push( '"' + safeJson(ruleid) + '"' ) ;
        }
        return ruleids ;
    }

    function cleanContent( val ) {
        val = val.replace( /“/g, '"' ).replace( /”/g, '"' ) ;
        val = val.replace( /‘/g, "'" ).replace( /’/g, "'" ) ;
        val = val.replace( /`/g, "'" ) ;
        val = val.replace( /–/g, "-" ) ;
        val = val.replace( />=/g, "&ge;" ).replace( /<=/g, "&le;" ) ;
        val = val.replace( /5\/8"/g, "&frac58;\"" ).replace( /1\/2"/g, "&half;\"" ) ;
        val = val.replace( /<q>/g, "<span class='quote'>" ).replace( /<\/q>/g, "</span>" ) ;
        val = val.replace( /\n/g, " " ) ;
        val = val.replace( /\s+/g, " " ) ;
        return val.trim() ;
    }

    function safeJson( val ) {
        return val.replace( /"/g, '\\"' ) ;
    }

    // process each Q+A
    var htmlBuf=[], jsonContent=[] ;
    var caption = $( "input.rules" ).val() ;
    $( ".qa" ).each( function() {
        var question = cleanContent( $(this).children( ".question" ).val() ) ;
        var answer = cleanContent( $(this).children( ".answer" ).val() ) ;
        // update the HTML preview
        htmlBuf.push( "<div class='question'>", "<img src='"+gQuestionImageUrl+"'>", question, "</div>" ) ;
        htmlBuf.push( "<div class='answer'>", "<img src='"+gAnswerImageUrl+"'>", answer, "</div>" ) ;
        // update the JSON preview
        if ( question ) {
            jsonContent.push( [
                '    { "question": "' + safeJson(question) + '",',
                '      "answers": [ [ "' + safeJson(answer) + '", "sr" ] ]',
                '    }'
            ].join( "\n" ) ) ;
        } else {
            jsonContent.push( [
                '    { "answers": [ [ "' + safeJson(answer) + '", "sr" ] ]',
                '    }'
            ].join( "\n" ) ) ;
        }
    } ) ;

    // update the previews
    $( "#html-preview" ).html( htmlBuf.join("") ) ;
    var jsonBuf = [] ;
    jsonBuf.push( '{ "caption": "' + safeJson(caption) + '",' ) ;
    var ruleids = extractRuleIds( caption ) ;
    if ( ruleids.length > 0 )
        jsonBuf.push( '  "ruleids": [ ' + ruleids.join(", ") + ' ],' ) ;
    jsonBuf.push( '  "content": [' ) ;
    jsonBuf.push( jsonContent.join( ",\n" ) ) ;
    jsonBuf.push( '  ]' ) ;
    jsonBuf.push( '}' ) ;
    $( "#json-preview" ).text( jsonBuf.join("\n") ) ;
}

// --------------------------------------------------------------------

$.fn.extend( {
    insertAtCaret: function( myValue ) {
        this.each( function() {
            if ( document.selection ) {
                this.focus() ;
                var sel = document.selection.createRange() ;
                sel.text = myValue ;
                this.focus() ;
            } else if ( this.selectionStart || this.selectionStart == "0" ) {
                var startPos = this.selectionStart ;
                var endPos = this.selectionEnd ;
                var scrollTop = this.scrollTop ;
                this.value = this.value.substring(0, startPos) + myValue + this.value.substring(endPos,this.value.length) ;
                this.focus() ;
                this.selectionStart = startPos + myValue.length ;
                this.selectionEnd = startPos + myValue.length ;
                this.scrollTop = scrollTop ;
            } else {
                this.value += myValue ;
                this.focus() ;
            }
        } ) ;
        return this ;
    }
} )  ;
