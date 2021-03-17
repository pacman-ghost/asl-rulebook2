import { gUrlParams } from "./MainApp.js" ;

// --------------------------------------------------------------------

const _HILITE_REGEXES = [
    new RegExp("!@:","g"), new RegExp(":@!","g"),
] ;

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

