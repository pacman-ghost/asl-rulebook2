import { gTargetIndex, gChapterResources, gUrlParams } from "./MainApp.js" ;

// --------------------------------------------------------------------

export function getPrimaryTarget( indexSearchResult )
{
    // identify the main target for a search result
    let ruleids = indexSearchResult.ruleids ;
    if ( ! ruleids )
        return null ;
    let targets = findTargets( ruleids[0], indexSearchResult.cset_id ) ;
    if ( targets && targets.length > 0 )
        return targets[0] ;
    return null ;
}

// - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -

export function findTargets( target, csetId )
{
    // check if the target is known to us
    let pos = target.indexOf( "-" ) ;
    if ( pos >= 0 ) {
        // NOTE: For ruleid's of the form "A12.3-.4", we want to target "A12.3".
        target = target.substring( 0, pos ) ;
    }
    let targets = gTargetIndex[ target.toLowerCase() ] ;
    if ( targets && csetId )
        targets = targets.filter( (m) => m.cset_id == csetId ) ;
    return targets ;
}

// - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -

export function isRuleid( val )
{
    // check if the value looks like a ruleid
    return val.match( /^[A-Z](\.|CG)?\d/ ) ;
}

// --------------------------------------------------------------------

const BEGIN_HIGHLIGHT = "!@:" ;
const END_HIGHLIGHT = ":@!" ;

const _HILITE_REGEXES = [
    new RegExp( BEGIN_HIGHLIGHT, "g" ),
    new RegExp( END_HIGHLIGHT, "g" ),
] ;

export function hasHilite( val ) {
    // check if the value has a highlighted term
    if ( val === undefined )
        return false ;
    return  val.indexOf( BEGIN_HIGHLIGHT ) !== -1 || val.indexOf( "<span class='hilite'>" ) !== -1 ;
}

export function fixupSearchHilites( val )
{
    // NOTE: The search engine highlights search tems in the returned search content using special markers.
    // We convert those markers to HTML span's here.
    if ( val === null || val === undefined )
        return val ;
    return val.replace( _HILITE_REGEXES[0], "<span class='hilite'>" )
              .replace( _HILITE_REGEXES[1], "</span>" ) ;
}

// --------------------------------------------------------------------

export function getChapterResource( rtype, chapterId )
{
    // get the URL for a chapter resource (if available)
    if ( ! gChapterResources[ rtype ] )
        return null ;
    return gChapterResources[ rtype ][ chapterId ] ;
}

// --------------------------------------------------------------------

export function showInfoMsg( msg ) { showNotificationMsg( "notice", msg ) ; }
export function showWarningMsg( msg ) { showNotificationMsg( "warning", msg ) ; }
export function showErrorMsg( msg ) { showNotificationMsg( "error", msg ) ; }

export function showNotificationMsg( msgType, msg )
{
    if ( gUrlParams.get( "store-msgs" ) ) {
        // store the message for the test suite
        $( "#_last-" + msgType + "-msg_" ).val( msg ) ;
        return ;
    }

    // show the notification message
    $.growl( {
        style: (msgType == "info") ? "notice" : msgType,
        title: null,
        message: msg,
        location: "br",
        duration: (msgType == "warning") ? 15*1000 : 5*1000,
        fixed: (msgType == "error"),
    } ) ;
}

