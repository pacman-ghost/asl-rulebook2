import { gContentDocs, gTargetIndex, gChapterResources, gEventBus, gUrlParams } from "./MainApp.js" ;

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

export function findTargets( ruleid, csetId )
{
    // NOTE: A "ruleid" is a rule ID (e.g. "A1.23") within a specific document. Hopefully, these will
    // be unique across the entire corpus, but we can't guarantee that (Chapter Z, anyone? :-/), so we
    // also have the concept of a "target", which is a ruleid plus the content set it's in.
    // One can only hope that ruleid's are unique in this context, even if there are multiple documents
    // in each content set...
    // NOTE: With vasl-templates integrations, there are destinations within the PDF that are not
    // actually ruleid's (i.e. Chapter H vehicle/ordnance notes), but we retain the old terminology,
    // since it will usually be the case.

    // check if the ruleid is known to us
    let match = ruleid.match( /-[0-9.]/ ) ;
    if ( match ) {
        // NOTE: For ruleid's of the form "A12.3-.4", we want to target "A12.3".
        ruleid = ruleid.substring( 0, match.index ) ;
    }
    let targets = gTargetIndex[ ruleid.toLowerCase() ] ;
    if ( targets && csetId )
        targets = targets.filter( (m) => m.cset_id == csetId ) ;
    return targets ;
}

// - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -

export function isRuleid( val )
{
    // check if the value looks like a ruleid
    // NOTE: "S" is for Fight For Seoul e.g. "FfS_S1" or "SmR_S2.3".
    return val.match( /^[A-Za-z]+_?(\.|CG|S)?\d/ ) ;
}

export function getASOPChapterIdFromSectionId( sectionId )
{
    // NOTE: Section ID's have the form "XXX-#", where XXX is the chapter ID and # is the sequence number.
    let pos = sectionId.lastIndexOf( "-" ) ;
    if ( pos < 0 )
        return null ;
    return sectionId.substring( 0, pos ) ;
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

export function linkifyAutoRuleids( $root )
{
    if ( ! gTargetIndex )
        return ; // nb: don't bother during this during startup

    // process each auto-detected ruleid
    $root.find( "span.auto-ruleid" ).each( function() {

        let ruleid = $(this).attr( "data-ruleid" ) ;
        let csetId = $(this).attr( "data-csetid" ) ;
        let targets = findTargets( ruleid, csetId ) ;
        if ( ! targets || targets.length == 0 ) {
            // nb: this would normally suggest an error, but there are things like e.g "Chapter B Terrain Chart" :-/
            return ;
        } else if ( targets.length != 1 )
            console.log( "WARNING: Found multiple targets for auto-ruleid: " + csetId + "/" + ruleid ) ;
        let target = targets[0] ;

        // add a label
        let caption = gContentDocs[ target.cdoc_id ].targets[ target.ruleid ].caption ;
        $(this).attr( "title", caption ) ;

        // make the ruleid clickable
        $(this).on( "click", function() {
            gEventBus.emit( "show-target", target.cdoc_id, target.ruleid ) ;
        } ) ;
        $(this).css( "cursor", "pointer" ) ;
    } ) ;
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
export function showWarningMsg( msg, info ) { showNotificationMsg( "warning", msg, info ) ; }
export function showErrorMsg( msg, info ) { showNotificationMsg( "error", msg, info ) ; }

export function showNotificationMsg( msgType, msg, info )
{
    if ( info )
        msg += " <div class='pre'>" + info + "</div>" ;

    if ( gUrlParams.get( "store-msgs" ) ) {
        // store the message for the test suite
        $( "#_last-" + msgType + "-msg_" ).val( msg ) ;
        return ;
    }

    // show the notification message
    let $growl = $.growl( {
        style: (msgType == "info") ? "notice" : msgType,
        title: null,
        message: msg,
        location: "br",
        duration: (msgType == "warning" || msgType == "footnote") ? 15*1000 : 5*1000,
        fixed: (msgType == "error"),
    } ).$growl() ;
    function onClick() {
        $growl.off( "click", onClick ) ;
        $(this).find( ".growl-close" ).click() ;
    }
    $growl.on( "click", onClick ) ;
    return $growl ;
}

export function hideFootnotes( fast )
{
    // hide the footnotes balloon
    if ( fast )
        $( ".growl-footnote" ).hide() ;
    else
        $( ".growl-footnote" ).find( ".growl-close" ).click() ;
}

// --------------------------------------------------------------------

export function makeImagesZoomable( $elem )
{
    // look for images that have been marked as zoomable, and make it so
    $elem.find( "img.imageZoom" ).each( function() {
        $(this).wrap( $( "<a>", {
            class: "imageZoom",
            href: $(this).attr( "src" ),
            title: "Click to zoom",
            onFocus: "javascript:this.blur()"
        } ) ) ;
    } ) ;
    $elem.find( "img.imageZoom" ).imageZoom( $ ) ;
}

export function makeImageUrl( fname )
{
    // generate an image URL
    let baseUrl = gImagesBaseUrl ; //eslint-disable-line no-undef
    if ( baseUrl[ baseUrl.length-1 ] != "/" )
        baseUrl += "/" ;
    if ( fname[0] == "/" )
        fname = fname.substring( 1 ) ;
    return baseUrl + fname ;
}

// --------------------------------------------------------------------

export function getJSON( url )
{
    // get the specified URL
    return new Promise( (resolve, reject) => {
        $.getJSON( url, (resp) => {
            resolve( resp ) ;
        } ).fail( (xhr, status, errorMsg) => {
            reject( errorMsg ) ;
        } ) ;
    } ) ;
}

export function getURL( url )
{
    // get the specified URL
    return new Promise( (resolve, reject) => {
        $.get( url, (resp) => {
            resolve( resp ) ;
        } ).fail( (xhr, status, errorMsg) => { //eslint-disable-line no-unused-vars
            reject( xhr ) ;
        } ) ;
    } ) ;
}

export function postURL( url, data )
{
    // post the data to the specified URL
    return new Promise( (resolve, reject) => {
        $.ajax( {
            url: url, type: "POST",
            data: data, dataType: "json"
        } ).done( (resp) => {
            resolve( resp ) ;
        } ).fail( (xhr, status, errorMsg) => {
            reject( errorMsg ) ;
        } ) ;
    } ) ;
}

// --------------------------------------------------------------------

export function wrapMatches( val, searchFor, delim1, delim2 )
{
    // search for a regex and wrap all matches with the specified delimiters
    if ( val == null || val == undefined )
        return null ;
    let buf = [] ;
    let pos = 0 ;
    for ( let match of val.matchAll( searchFor ) ) {
        buf.push(
            val.substring( pos, match.index ),
            delim1, match[0], delim2
        ) ;
        pos = match.index + match[0].length ;
    }
    buf.push( val.substring( pos ) ) ;
    return buf.join("") ;
}

export function wrapExcBlocks( val )
{
    // search for "[EXC: ...]" blocks and wrap them in a <span>
    return wrapMatches( val,
        new RegExp( /\[EXC: .*?\]/g ),
        "<span class='exc'>", "</span>"
    ) ;
}

export function isChildOf( elem, elemParent, strict )
{
    // check if an element is a child of another element
    if ( $.contains( elemParent, elem ) )
        return true ;
    if ( ! strict && elem.isSameNode( elemParent ) )
        return true ;
}

export function getCssSize( elem, attr )
{
    // return the element's size
    attr = $(elem).css( attr ) ;
    if ( attr.substring( attr.length-2 ) == "px" )
        attr = attr.substring( 0, attr.length-2 ) ;
    return parseInt( attr ) ;
}
