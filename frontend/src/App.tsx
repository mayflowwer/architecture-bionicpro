import { useEffect, useState } from 'react';
import Keycloak from 'keycloak-js';
import ReportPage from './components/ReportPage';

const keycloak = new Keycloak({
  url: process.env.REACT_APP_KEYCLOAK_URL || '',
  realm: process.env.REACT_APP_KEYCLOAK_REALM || '',
  clientId: process.env.REACT_APP_KEYCLOAK_CLIENT_ID || '',
});

const App: React.FC = () => {
  const [initialized, setInitialized] = useState(false);
  const [authenticated, setAuthenticated] = useState(false);

  useEffect(() => {
    keycloak
      .init({
        onLoad: 'login-required',
        pkceMethod: 'S256',
        responseMode: 'query',
        checkLoginIframe: false,
      })
      .then((auth) => {
        console.log('init auth:', auth);

        setAuthenticated(auth);
        setInitialized(true);
      })
      .catch((err) => {
        console.error('keycloak init error', err);
      });
  }, []);

  if (!initialized) {
    return <div>Loading...</div>;
  }

  if (!authenticated) {
    return <div>Not authenticated</div>;
  }

  return (
    <div className="App">
      <ReportPage keycloak={keycloak} />
    </div>
  );
};

export default App;