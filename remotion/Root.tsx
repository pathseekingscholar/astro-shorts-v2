import React from "react";
import {Composition} from "remotion";
import {AstroShortRemotionRoot, astroShortDuration} from "./AstroShort";
import {sampleScriptData} from "./sample-props";
import type {AstroScriptData} from "./types";

export const RemotionRoot: React.FC = () => {
  const defaultProps: {scriptData: AstroScriptData} = {
    scriptData: sampleScriptData,
  };

  return (
    <Composition
      id="AstroShort"
      component={AstroShortRemotionRoot}
      width={1080}
      height={1920}
      fps={30}
      durationInFrames={astroShortDuration(defaultProps.scriptData)}
      defaultProps={defaultProps}
    />
  );
};
