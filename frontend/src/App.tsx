import React from 'react';
import { InterviewProvider } from './context/InterviewContext';
import { CandidateInterviewFlow } from './components/candidate/CandidateInterviewFlow';

export const App: React.FC = () => {
  return (
    <InterviewProvider>
      <CandidateInterviewFlow />
    </InterviewProvider>
  );
};

export default App;


