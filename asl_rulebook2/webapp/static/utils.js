export function showInfoMsg( msg ) { _doShowNotificationMsg( "notice", msg ) ; }
export function showWarningMsg( msg ) { _doShowNotificationMsg( "warning", msg ) ; }
export function showErrorMsg( msg ) { _doShowNotificationMsg( "error", msg ) ; }

function _doShowNotificationMsg( msgType, msg )
{
    // show the notification message
    $.growl( {
        style: msgType,
        title: null,
        message: msg,
        location: "br",
        duration: (msgType == "warning") ? 15*1000 : 5*1000,
        fixed: (msgType == "error"),
    } ) ;
}

