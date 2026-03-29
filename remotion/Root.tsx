import React from "react";
import {Composition} from "remotion";
import {AstroShortComposition, astroShortDuration} from "./AstroShort";
import {sampleScriptData} from "./sample-props";
import {compositionIdForStyle, type RenderStyleChoice} from "./style-system";
import type {AstroRenderProps} from "./types";

const sharedProps = {
  scriptData: sampleScriptData,
};

const styles: RenderStyleChoice[] = [
  "auto",
  "planet_character",
  "educational_voiceless",
  "character_explainer",
];

export const RemotionRoot: React.FC = () => {
  return (
    <>
      {styles.map((styleId) => {
        const id = compositionIdForStyle(styleId);
        return (
          <Composition
            key={id}
            id={id}
            component={AstroShortComposition}
            width={1080}
            height={1920}
            fps={30}
            calculateMetadata={({props}) => {
              const renderProps = (props ?? sharedProps) as AstroRenderProps;
              return {
                durationInFrames: astroShortDuration(renderProps.scriptData),
              };
            }}
            defaultProps={{
              ...sharedProps,
              styleId,
            }}
          />
        );
      })}
    </>
  );
};
