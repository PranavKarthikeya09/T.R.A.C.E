interface WorkflowRailProps {
  hasFile: boolean;
  isAnalyzing: boolean;
  hasResult: boolean;
}

const stages = ['Intake', 'Examine', 'Interpret', 'Document'];

export const WorkflowRail: React.FC<WorkflowRailProps> = ({ hasFile, isAnalyzing, hasResult }) => {
  const activeIndex = hasResult ? 3 : isAnalyzing ? 1 : hasFile ? 1 : 0;

  return (
    <nav className="workflow-rail" aria-label="Investigation workflow">
      <ol>
        {stages.map((stage, index) => {
          const isComplete = hasResult && index < activeIndex;
          const isCurrent = index === activeIndex;

          return (
            <li
              key={stage}
              className={`workflow-stage${isComplete ? ' is-complete' : ''}${isCurrent ? ' is-current' : ''}`}
              aria-current={isCurrent ? 'step' : undefined}
            >
              <span className="workflow-stage-number font-mono">0{index + 1}</span>
              <span className="workflow-stage-name">{stage}</span>
            </li>
          );
        })}
      </ol>
      <p className="workflow-caption font-mono">
        {isAnalyzing ? 'ANALYSIS REQUEST IN PROGRESS' : hasResult ? 'RESULTS READY FOR REVIEW' : hasFile ? 'IMAGE READY FOR EXAMINATION' : 'BEGIN WITH AN IMAGE'}
      </p>
    </nav>
  );
};
