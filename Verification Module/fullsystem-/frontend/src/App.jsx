import { useState } from "react";
import AadhaarUpload from "./components/AadhaarUpload";
import FaceVerify from "./components/FaceVerify";
import WebcamVerify from "./components/WebcamVerify";

function App() {

  const [uniqueId, setUniqueId] = useState(null);
  const [faceDone, setFaceDone] = useState(false);

  return (

    <div style={{padding:40}}>

      <h1>Interview Identity System</h1>

      {!uniqueId && (
        <AadhaarUpload setUniqueId={setUniqueId}/>
      )}

      {uniqueId && !faceDone && (
        <FaceVerify setNext={setFaceDone}/>
      )}

      {faceDone && (
        <WebcamVerify/>
      )}

    </div>

  );
}

export default App;