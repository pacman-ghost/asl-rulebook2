// create the main application
export const gPrepareApp = Vue.createApp( { //eslint-disable-line no-undef
    template: "<prepare-app />",
} ) ;
$(document).ready( () => {
    gPrepareApp.mount( "#prepare-app" ) ;
} ) ;

// parse any URL parameters
let gUrlParams = new URLSearchParams( window.location.search.substring(1) ) ;

let gProgressPanel = null ;

// --------------------------------------------------------------------

gPrepareApp.component( "prepare-app", {

    data() { return {
        isLoaded: false,
        isProcessing: false,
        downloadUrl: null,
        fatalErrorMsg: gHaveGhostscript ? null : "Ghostscript is not available.", //eslint-disable-line no-undef
        fatalErrorIconUrl: makeImageUrl( "error.png" ),
    } ; },

    template: `
<div id="main">
    <div id="header">
        No data directory has been configured.
        <p> If you haven't used this program before, a few things need to be prepared first.
            It will take around 10-15 minutes.
        </p>
        <p> If there are problems, you can try to prepare your data files manually,
            as described <a href="/doc/prepare.md" target="_blank">here</a>.
        </p>
    </div>
    <div v-show=fatalErrorMsg id="fatal-error" >
        <img :src=fatalErrorIconUrl style="float:left;margin-right:5px;" />
        {{fatalErrorMsg}}
    </div>
    <upload-panel v-show="!fatalErrorMsg &&!isProcessing" @file-selected=onFileSelected />
    <progress-panel v-show=isProcessing @done=onDone @fatal=onFatalError ref=progressPanel />
    <download-panel v-show=downloadUrl :downloadUrl=downloadUrl ref=downloadPanel />
    <textarea id="testing-zip-data" style="display:none;" />
    <div v-if=isLoaded id="_prepareapp-loaded_" />
</div>`,

    mounted() {
        // initialize the UI
        $( "button" ).button() ;
        this.isLoaded = true ;
    },

    methods: {

        onFileSelected( file ) {
            this.isProcessing = true ;
            if ( ! file ) {
                // this is a test of progress logging
                this.uploadPdfData( null ) ;
                return ;
            }
            if ( typeof file == "string" ) {
                // this is PDF file data given to us by the test suite - just return it as is
                this.uploadPdfData( file ) ;
                return ;
            }
            this.$nextTick( () => {
                gProgressPanel.addStatusBlock( "Uploading the PDF..." ) ;
                // read the selected file
                let fileReader = new FileReader() ;
                fileReader.onload = () => {
                    let pdfData = fileReader.result ;
                    pdfData = removeBase64Prefix( pdfData ) ;
                    this.uploadPdfData( pdfData ) ;
                } ;
                fileReader.readAsDataURL( file ) ;
            } ) ;
        },

        uploadPdfData( pdfData ) {
            // upload the PDF file to the backend
            let data = { pdfData: pdfData } ;
            if ( gUrlParams.get( "test" ) ) {
                [ "npasses", "status", "warnings", "errors", "delay" ].forEach( (arg) => {
                    let val = gUrlParams.get( arg ) ;
                    if ( val )
                        data[arg] = val ;
                } ) ;
            }
            $.ajax( {
                url: gPrepareDataFilesUrl, //eslint-disable-line no-undef
                type: "POST",
                data: JSON.stringify( data ),
                contentType: "application/json",
            } ).done( () => {
                // tell the backend to start processing
                gProgressPanel.socketIOClient.emit( "start" ) ;
            } ).fail( (xhr, status, errorMsg) => {
                this.fatalErrorMsg = "Couldn't start processing: " + errorMsg ;
            } ) ;
        },

        onDone( downloadUrl ) {
            // make the download available to the user
            $( this.$refs.progressPanel.$el ).css( {
                background: "#f0f0f0", color: "#444",
                "border-color": "#aaa",
            } ) ;
            this.downloadUrl = downloadUrl ;
        },

        onFatalError( msg ) {
            this.fatalErrorMsg = msg ;
        },

    },

} ) ;

// --------------------------------------------------------------------

gPrepareApp.component( "upload-panel", {

    data() { return {
        isTestMode: gUrlParams.get( "test" ),
        uploadIconUrl: makeImageUrl( "eASLRB.png" ),
    } ; },

    template: `
<div id="upload-panel">
    <div v-if=isTestMode>
        <button @click=startTest style="height:28px;" > Go </button>
        Click on the button to start a test run.
    </div>
    <div v-else style="display:flex;">
        <input type="file" @change=onFileSelected accept=".pdf" style="display:none;" ref="selectFile" >
        <button @click=onUploadProxy id="upload-proxy" ref="uploadProxy"> <img :src=uploadIconUrl /> </button>
        <div style="width:29em;">
            Click on the button, and select your copy of MMP's eASLRB.
            <div class="info"> You <u>must</u> use the <a href="https://www.wargamevault.com/product/344879/Electronic-Advanced-Squad-Leader-Rulebook" target="_blank">offical MMP eASLRB</a>. <br>
                A scan of a printed rulebook <u>will not work</u>!
                <p> You should use v1.07 of the eASLRB PDF (normal version, not the "inherited zoom" version). Other versions <i>may</i> work, but may have warnings and/or errors. </p>
            </div>
        </div>
    </div>
</div>`,

    methods: {

        onUploadProxy() {
            // check if the test suite has left us some PDF file data to use
            let $elem = $( "#testing-zip-data" ) ;
            if ( $elem.length > 0 && $elem.val().length > 0 ) {
                // yup - just return that
                this.$emit( "file-selected", $elem.val() ) ;
                $elem.val( "" ) ;
                return ;
            }
            $elem.remove() ; // nb: this tells download-panel we are not being run by the test suite
            // NOTE: It's difficult to style a file <input> element, so we make it hidden, and present
            // a <button> element to the user, that clicks on the real file <input> when it is clicked.
            this.$refs.selectFile.click() ;
        },

        onFileSelected( evt ) {
            // NOTE: We would normally read the file here, but it takes some time because of its size,
            // so we return the file object to the parent, so it can close us and open the progress panel,
            // showing the "Uploading PDF" message, *then* we read the file and upload it.
            this.$emit( "file-selected", evt.target.files[0] ) ;
        },

        startTest() {
            this.$emit( "file-selected", null ) ;
        },

    },

} ) ;

// --------------------------------------------------------------------

gPrepareApp.component( "progress-panel", {

    data() { return {
        socketIOClient: null,
        statusBlocks: [],
        isDone: false,
    } ; },

    template: `
<div id="progress-panel">
    <status-block v-for="sb in statusBlocks" :statusBlock=sb :key=sb />
    <div v-if="!isDone" class="loading">
        <img src="/static/images/loading.gif" />
        <div style="margin-top:3px;">
            While you're waiting, you can <br> check out the features <a href="/doc/features/index.html" target="_blank">here</a>.
        </div>
    </div>
</div>`,

    created() {
        // initialize
        gProgressPanel = this ;
        this.initSocketIOClient() ;
    },

    methods: {

        initSocketIOClient() {
            // initialize the socketio client
            this.socketIOClient = io.connect() ; //eslint-disable-line no-undef
            this.socketIOClient.on( "disconnect", () => {
                if ( ! this.isDone )
                    this.$emit( "fatal", "The server has gone away. Please restart it, then reload this page." ) ;
            } ) ;
            this.socketIOClient.on( "status", (msg) => { this.addStatusBlock( msg ) ; } ) ;
            this.socketIOClient.on( "progress", (msg) => { this.addProgressMsg( "info", msg ) ; } ) ;
            this.socketIOClient.on( "warning", (msg) => { this.addProgressMsg( "warning", msg ) ; } ) ;
            this.socketIOClient.on( "error", (msg) => { this.addProgressMsg( "error", msg ) ; } ) ;
            this.socketIOClient.on( "done", (downloadUrl) => {
                this.isDone = true ;
                gProgressPanel.addStatusBlock( "All done." ) ;
                this.socketIOClient.disconnect() ;
                this.socketIOClient = null ;
                this.$emit( "done", downloadUrl ) ;
            } ) ;
        },

        addStatusBlock( statusMsg ) {
            // de-activate the previous status block
            if ( this.statusBlocks.length > 0 )
                this.statusBlocks[ this.statusBlocks.length-1 ].isActive = false ;
            // start a new status block
            this.statusBlocks.push( {
                status: statusMsg, progress: [],
                isActive: true
            } ) ;
        },

        addProgressMsg( msgType, msg ) {
            // add a progress message to the current status block
            if ( this.statusBlocks.length == 0 )
                this.addStatusBlock( "" ) ;
            this.statusBlocks[ this.statusBlocks.length-1 ].progress.push( [ msgType, msg ] ) ;
        },

    },

} ) ;

// - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -

gPrepareApp.component( "status-block", {

    props: [ "statusBlock" ],

    template: `
<div class="status">
    <div class="caption"> {{statusBlock.status}} </div>
    <table v-if="statusBlock.progress.length > 0" >
        <tr v-for="(p,pno) in statusBlock.progress" v-show="showProgress(p,pno)" >
            <td> <img :src=makeIconUrl(p) :style=makeIconCss(p) class="icon" /> </td>
            <td v-html=p[1] />
        </tr>
    </table>
</div>`,

    methods: {

        showProgress( progress, progressNo ) {
            // figure out if we should show a progress message or not
            if ( progress[0] != "info" )
                return true ; // nb: always show warnings/errors
            if ( this.statusBlock.isActive && progressNo == this.statusBlock.progress.length-1 )
                return true ; // nb: show the last progress message of the last status block
            return false ;
        },

        makeIconUrl( progress ) {
            if ( progress[0] == "info" )
                return makeImageUrl( "bullet2.png" ) ;
            return makeImageUrl( progress[0] + ".png" ) ;
        },
        makeIconCss( progress ) {
            if ( progress[0] == "info" )
                return "height: 8px ; padding-left: 4px ;" ;
        },

    },

} ) ;

// - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -

gPrepareApp.component( "download-panel", {

    props: [ "downloadUrl" ],
    data() { return {
        downloadIconUrl: makeImageUrl( "download.png" ),
    } ; },

    template: `
<div id="download-panel">
    <div style="display:flex;margin-bottom:10px;">
        <button @click=onDownload id="download"> <img :src=downloadIconUrl /> </button>
        <div> Your data files are ready.
            <p> Click on the button to download them, and unpack them into a directory somewhere. </p>
        </div>
    </div>
    <div> Then restart the server with a <span class="pre">--data</span> parameter pointing to that directory e.g.
            <code> ./run-server.py --data ... </code>
        or
            <code> ./run-container.sh --data ... </code>
    </div>
    <div class="info">
        You can edit the generated data files directly, if you want to make changes.
        <p> If you want to make changes permanent (so they happen if you redo this preparation process), check out the files in <span class="pre">$/asl_rulebook2/extract/data/</span>. </p>
    </div>
</div>`,

    methods: {

        onDownload() {
            if ( ! this.downloadUrl ) {
                alert( "The download is not ready." ) ; // nb: should never get here!
                return ;
            }
            // check if we are being run by the test suite
            let $elem = $( "#testing-zip-data" ) ;
            if ( $elem.length == 0 ) {
                // nope - just return the download directly to the user
                window.location.href = this.downloadUrl ;
                return ;
            }
            // yup - download the ZIP file and make it available to the test suite
            // FUDGE! Setting the response type in a jQuery Ajax request:
            //   $.ajax( { type: "GET", url: ...,
            //       xhrFields: { responseType: "arraybuffer" }
            //   } ) ;
            // should work, but doesn't :-/ Instead, we do it by providing a custom XHR object
            // to manage the download. Things are slow, but this only used by the test suite.
            let xhrOverride = new XMLHttpRequest() ;
            xhrOverride.responseType = "blob" ;
            $.ajax( {
                type: "GET", url: this.downloadUrl,
                xhr: function() { return xhrOverride ; },
            } ).done( () => {
                // read the response
                let fileReader = new FileReader() ;
                fileReader.onload = function( evt ){
                    let zip_data = evt.target.result ;
                    // make the response available to the test suite
                    $( "#testing-zip-data" ).val( removeBase64Prefix( zip_data ) ) ;
                };
                fileReader.readAsDataURL( xhrOverride.response ) ;
            } ).fail( (xhr, status, errorMsg) => {
                alert( "Download failed: " + errorMsg ) ;
            } ) ;
        },
    },

} ) ;

// --------------------------------------------------------------------

function makeImageUrl( fname ) {
    return gImagesBaseUrl + "/" + fname ; //eslint-disable-line no-undef
}

function removeBase64Prefix( val )
{
    // remove the base64 prefix from the start of the string
    // - data: MIME-TYPE ; base64 , ...
    return val.replace( /^data:.*?;base64,/, "" ) ;
}
