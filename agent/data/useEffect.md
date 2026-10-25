[API Reference](https://react.dev/reference/react)

[Hooks](https://react.dev/reference/react/hooks)

# useEffect

`useEffect` is a React Hook that lets you [synchronize a component with an external system.](https://react.dev/learn/synchronizing-with-effects)

```
useEffect(setup, dependencies?)
```
- [Reference ](https://react.dev/reference/react/useEffect#reference)

    - [`useEffect(setup, dependencies?)`](https://react.dev/reference/react/useEffect#useeffect)

- [Usage ](https://react.dev/reference/react/useEffect#usage)

    - [Connecting to an external system ](https://react.dev/reference/react/useEffect#connecting-to-an-external-system)

    - [Wrapping Effects in custom Hooks ](https://react.dev/reference/react/useEffect#wrapping-effects-in-custom-hooks)

    - [Controlling a non-React widget ](https://react.dev/reference/react/useEffect#controlling-a-non-react-widget)

    - [Fetching data with Effects ](https://react.dev/reference/react/useEffect#fetching-data-with-effects)

    - [Specifying reactive dependencies ](https://react.dev/reference/react/useEffect#specifying-reactive-dependencies)

    - [Updating state based on previous state from an Effect ](https://react.dev/reference/react/useEffect#updating-state-based-on-previous-state-from-an-effect)

    - [Removing unnecessary object dependencies ](https://react.dev/reference/react/useEffect#removing-unnecessary-object-dependencies)

    - [Removing unnecessary function dependencies ](https://react.dev/reference/react/useEffect#removing-unnecessary-function-dependencies)

    - [Reading the latest props and state from an Effect ](https://react.dev/reference/react/useEffect#reading-the-latest-props-and-state-from-an-effect)

    - [Displaying different content on the server and the client ](https://react.dev/reference/react/useEffect#displaying-different-content-on-the-server-and-the-client)

- [Troubleshooting ](https://react.dev/reference/react/useEffect#troubleshooting)

    - [My Effect runs twice when the component mounts ](https://react.dev/reference/react/useEffect#my-effect-runs-twice-when-the-component-mounts)

    - [My Effect runs after every re-render ](https://react.dev/reference/react/useEffect#my-effect-runs-after-every-re-render)

    - [My Effect keeps re-running in an infinite cycle ](https://react.dev/reference/react/useEffect#my-effect-keeps-re-running-in-an-infinite-cycle)

    - [My cleanup logic runs even though my component didn’t unmount ](https://react.dev/reference/react/useEffect#my-cleanup-logic-runs-even-though-my-component-didnt-unmount)

    - [My Effect does something visual, and I see a flicker before it runs ](https://react.dev/reference/react/useEffect#my-effect-does-something-visual-and-i-see-a-flicker-before-it-runs)

## Reference 

### `useEffect(setup, dependencies?)`

Call `useEffect` at the top level of your component to declare an Effect:

```
import { useState, useEffect } from 'react';

import { createConnection } from './chat.js';

function ChatRoom({ roomId }) {

  const [serverUrl, setServerUrl] = useState('https://localhost:1234');

  useEffect(() => {

    const connection = createConnection(serverUrl, roomId);

    connection.connect();

    return () => {

      connection.disconnect();

    };

  }, [serverUrl, roomId]);

  // ...

}
```
[See more examples below.](https://react.dev/reference/react/useEffect#usage)

#### Parameters 

- `setup`: The function with your Effect’s logic. Your setup function may also optionally return a *cleanup* function. When your [component commits](https://react.dev/learn/render-and-commit#step-3-react-commits-changes-to-the-dom), React will run your setup function. After every commit with changed dependencies, React will first run the cleanup function (if you provided it) with the old values, and then run your setup function with the new values. After your component is removed from the DOM, React will run your cleanup function.

- **optional** `dependencies`: The list of all reactive values referenced inside of the `setup` code. Reactive values include props, state, and all the variables and functions declared directly inside your component body. If your linter is [configured for React](https://react.dev/learn/editor-setup#linting), it will verify that every reactive value is correctly specified as a dependency. The list of dependencies must have a constant number of items and be written inline like `[dep1, dep2, dep3]`. React will compare each dependency with its previous value using the [`Object.is`](https://developer.mozilla.org/en-US/docs/Web/JavaScript/Reference/Global_Objects/Object/is) comparison. If you omit this argument, your Effect will re-run after every commit of the component. [See the difference between passing an array of dependencies, an empty array, and no dependencies at all.](https://react.dev/reference/react/useEffect#examples-dependencies)

#### Returns 

`useEffect` returns `undefined`.

#### Caveats 

- `useEffect` is a Hook, so you can only call it **at the top level of your component**  or your own Hooks. You can’t call it inside loops or conditions. If you need that, extract a new component and move the state into it.

- If you’re **not trying to synchronize with some external system,** [you probably don’t need an Effect.](https://react.dev/learn/you-might-not-need-an-effect)

- When Strict Mode is on, React will **run one extra development-only setup+cleanup cycle**  before the first real setup. This is a stress-test that ensures that your cleanup logic “mirrors” your setup logic and that it stops or undoes whatever the setup is doing. If this causes a problem, [implement the cleanup function.](https://react.dev/learn/synchronizing-with-effects#how-to-handle-the-effect-firing-twice-in-development)

- If some of your dependencies are objects or functions defined inside the component, there is a risk that they will **cause the Effect to re-run more often than needed.**  To fix this, remove unnecessary [object](https://react.dev/reference/react/useEffect#removing-unnecessary-object-dependencies) and [function](https://react.dev/reference/react/useEffect#removing-unnecessary-function-dependencies) dependencies. You can also [extract state updates](https://react.dev/reference/react/useEffect#updating-state-based-on-previous-state-from-an-effect) and [non-reactive logic](https://react.dev/reference/react/useEffect#reading-the-latest-props-and-state-from-an-effect) outside of your Effect.

- If your Effect wasn’t caused by an interaction (like a click), React will generally let the browser **paint the updated screen first before running your Effect.**  If your Effect is doing something visual (for example, positioning a tooltip), and the delay is noticeable (for example, it flickers), replace `useEffect` with [`useLayoutEffect`.](https://react.dev/reference/react/useLayoutEffect)

- If your Effect is caused by an interaction (like a click), **React may run your Effect before the browser paints the updated screen** . This ensures that the result of the Effect can be observed by the event system. Usually, this works as expected. However, if you must defer the work until after paint, such as an `alert()`, you can use `setTimeout`. See [reactwg/react-18/128](https://github.com/reactwg/react-18/discussions/128) for more information.

- Even if your Effect was caused by an interaction (like a click), **React may allow the browser to repaint the screen before processing the state updates inside your Effect.**  Usually, this works as expected. However, if you must block the browser from repainting the screen, you need to replace `useEffect` with [`useLayoutEffect`.](https://react.dev/reference/react/useLayoutEffect)

- Effects **only run on the client.**  They don’t run during server rendering.

## Usage 

### Connecting to an external system 

Some components need to stay connected to the network, some browser API, or a third-party library, while they are displayed on the page. These systems aren’t controlled by React, so they are called *external.*

To [connect your component to some external system,](https://react.dev/learn/synchronizing-with-effects) call `useEffect` at the top level of your component:

```
import { useState, useEffect } from 'react';

import { createConnection } from './chat.js';

function ChatRoom({ roomId }) {

  const [serverUrl, setServerUrl] = useState('https://localhost:1234');

  useEffect(() => {

  	const connection = createConnection(serverUrl, roomId);

    connection.connect();

  	return () => {

      connection.disconnect();

  	};

  }, [serverUrl, roomId]);

  // ...

}
```
You need to pass two arguments to `useEffect`:

1. A *setup function* with setup code that connects to that system.

    - It should return a *cleanup function* with cleanup code that disconnects from that system.

2. A list of dependencies including every value from your component used inside of those functions.

**React calls your setup and cleanup functions whenever it’s necessary, which may happen multiple times:**

1. Your setup code runs when your component is added to the page *(mounts)*.

2. After every commit of your component where the dependencies have changed:

    - First, your cleanup code runs with the old props and state.

    - Then, your setup code runs with the new props and state.

3. Your cleanup code runs one final time after your component is removed from the page *(unmounts).*

**Let’s illustrate this sequence for the example above.**

When the `ChatRoom` component above gets added to the page, it will connect to the chat room with the initial `serverUrl` and `roomId`. If either `serverUrl` or `roomId` change as a result of a commit (say, if the user picks a different chat room in a dropdown), your Effect will *disconnect from the previous room, and connect to the next one.* When the `ChatRoom` component is removed from the page, your Effect will disconnect one last time.

**To [help you find bugs,](https://react.dev/learn/synchronizing-with-effects#step-3-add-cleanup-if-needed) in development React runs setup and cleanup one extra time before the setup.**  This is a stress-test that verifies your Effect’s logic is implemented correctly. If this causes visible issues, your cleanup function is missing some logic. The cleanup function should stop or undo whatever the setup function was doing. The rule of thumb is that the user shouldn’t be able to distinguish between the setup being called once (as in production) and a *setup* → *cleanup* → *setup* sequence (as in development). [See common solutions.](https://react.dev/learn/synchronizing-with-effects#how-to-handle-the-effect-firing-twice-in-development)

**Try to [write every Effect as an independent process](https://react.dev/learn/lifecycle-of-reactive-effects#each-effect-represents-a-separate-synchronization-process) and [think about a single setup/cleanup cycle at a time.](https://react.dev/learn/lifecycle-of-reactive-effects#thinking-from-the-effects-perspective)**  It shouldn’t matter whether your component is mounting, updating, or unmounting. When your cleanup logic correctly “mirrors” the setup logic, your Effect is resilient to running setup and cleanup as often as needed.

### Note

An Effect lets you [keep your component synchronized](https://react.dev/learn/synchronizing-with-effects) with some external system (like a chat service). Here, *external system* means any piece of code that’s not controlled by React, such as:

- A timer managed with [`setInterval()`](https://developer.mozilla.org/en-US/docs/Web/API/setInterval) and [`clearInterval()`](https://developer.mozilla.org/en-US/docs/Web/API/clearInterval).

- An event subscription using [`window.addEventListener()`](https://developer.mozilla.org/en-US/docs/Web/API/EventTarget/addEventListener) and [`window.removeEventListener()`](https://developer.mozilla.org/en-US/docs/Web/API/EventTarget/removeEventListener).

- A third-party animation library with an API like `animation.start()` and `animation.reset()`.

**If you’re not connecting to any external system, [you probably don’t need an Effect.](https://react.dev/learn/you-might-not-need-an-effect)**

#### Examples of connecting to an external system

1. Connecting to a chat server 2. Listening to a global browser event 3. Triggering an animation 4. Controlling a modal dialog 5. Tracking element visibility 

#### 
Example 1 of 5: Connecting to a chat server 

In this example, the `ChatRoom` component uses an Effect to stay connected to an external system defined in `chat.js`. Press “Open chat” to make the `ChatRoom` component appear. This sandbox runs in development mode, so there is an extra connect-and-disconnect cycle, as [explained here.](https://react.dev/learn/synchronizing-with-effects#step-3-add-cleanup-if-needed) Try changing the `roomId` and `serverUrl` using the dropdown and the input, and see how the Effect re-connects to the chat. Press “Close chat” to see the Effect disconnect one last time.

App.jschat.js

App.js

```
import { useState, useEffect } from 'react'; import { createConnection } from './chat.js'; function ChatRoom({ roomId }) {
  const [serverUrl, setServerUrl] = useState('https://localhost:1234');

  useEffect(() => {
    const connection = createConnection(serverUrl, roomId);
    connection.connect();
    return () => {
      connection.disconnect();
    };
  }, [roomId, serverUrl]);

  return (
    <>
      <label>
 Server URL:{' '}
        <input
          value={serverUrl}
          onChange={e => setServerUrl(e.target.value)}
        />
      </label>
      <h1>Welcome to the {roomId} room!</h1>
    </>
  ); } export default function App() {
  const [roomId, setRoomId] = useState('general');
  const [show, setShow] = useState(false);
  return (
    <>
      <label>
 Choose the chat room:{' '}
        <select
          value={roomId}
          onChange={e => setRoomId(e.target.value)}
        >
          <option value="general">general</option>
          <option value="travel">travel</option>
          <option value="music">music</option>
        </select>
      </label>
      <button onClick={() => setShow(!show)}>
        {show ? 'Close chat' : 'Open chat'}
      </button>
      {show && <hr />}
      {show && <ChatRoom roomId={roomId} />}
    </>
  ); } 
```
Next Example

### Wrapping Effects in custom Hooks 

Effects are an [“escape hatch”:](https://react.dev/learn/escape-hatches) you use them when you need to “step outside React” and when there is no better built-in solution for your use case. If you find yourself often needing to manually write Effects, it’s usually a sign that you need to extract some [custom Hooks](https://react.dev/learn/reusing-logic-with-custom-hooks) for common behaviors your components rely on.

For example, this `useChatRoom` custom Hook “hides” the logic of your Effect behind a more declarative API:

```
function useChatRoom({ serverUrl, roomId }) {

  useEffect(() => {

    const options = {

      serverUrl: serverUrl,

      roomId: roomId

    };

    const connection = createConnection(options);

    connection.connect();

    return () => connection.disconnect();

  }, [roomId, serverUrl]);

}
```
Then you can use it from any component like this:

```
function ChatRoom({ roomId }) {

  const [serverUrl, setServerUrl] = useState('https://localhost:1234');

  useChatRoom({

    roomId: roomId,

    serverUrl: serverUrl

  });

  // ...
```
There are also many excellent custom Hooks for every purpose available in the React ecosystem.

[Learn more about wrapping Effects in custom Hooks.](https://react.dev/learn/reusing-logic-with-custom-hooks)

#### Examples of wrapping Effects in custom Hooks

1. Custom `useChatRoom` Hook 2. Custom `useWindowListener` Hook 3. Custom `useIntersectionObserver` Hook 

#### 
Example 1 of 3: Custom `useChatRoom` Hook 

This example is identical to one of the [earlier examples,](https://react.dev/reference/react/useEffect#examples-connecting) but the logic is extracted to a custom Hook.

App.jsuseChatRoom.jschat.js

App.js

```
import { useState } from 'react'; import { useChatRoom } from './useChatRoom.js'; function ChatRoom({ roomId }) {
  const [serverUrl, setServerUrl] = useState('https://localhost:1234');

  useChatRoom({
    roomId: roomId,
    serverUrl: serverUrl
  });

  return (
    <>
      <label>
 Server URL:{' '}
        <input
          value={serverUrl}
          onChange={e => setServerUrl(e.target.value)}
        />
      </label>
      <h1>Welcome to the {roomId} room!</h1>
    </>
  ); } export default function App() {
  const [roomId, setRoomId] = useState('general');
  const [show, setShow] = useState(false);
  return (
    <>
      <label>
 Choose the chat room:{' '}
        <select
          value={roomId}
          onChange={e => setRoomId(e.target.value)}
        >
          <option value="general">general</option>
          <option value="travel">travel</option>
          <option value="music">music</option>
        </select>
      </label>
      <button onClick={() => setShow(!show)}>
        {show ? 'Close chat' : 'Open chat'}
      </button>
      {show && <hr />}
      {show && <ChatRoom roomId={roomId} />}
    </>
  ); } 
```
Next Example

### Controlling a non-React widget 

Sometimes, you want to keep an external system synchronized to some prop or state of your component.

For example, if you have a third-party map widget or a video player component written without React, you can use an Effect to call methods on it that make its state match the current state of your React component. This Effect creates an instance of a `MapWidget` class defined in `map-widget.js`. When you change the `zoomLevel` prop of the `Map` component, the Effect calls the `setZoom()` on the class instance to keep it synchronized:

App.jsMap.jsmap-widget.js

Map.js

```
import { useRef, useEffect } from 'react'; import { MapWidget } from './map-widget.js'; export default function Map({ zoomLevel }) {
  const containerRef = useRef(null);
  const mapRef = useRef(null);

  useEffect(() => {
    if (mapRef.current === null) {
      mapRef.current = new MapWidget(containerRef.current);
    }

    const map = mapRef.current;
    map.setZoom(zoomLevel);
  }, [zoomLevel]);

  return (
    <div
      style={{ width: 200, height: 200 }}
      ref={containerRef}
    />
  ); } 
```
In this example, a cleanup function is not needed because the `MapWidget` class manages only the DOM node that was passed to it. After the `Map` React component is removed from the tree, both the DOM node and the `MapWidget` class instance will be automatically garbage-collected by the browser JavaScript engine.

### Fetching data with Effects 

You can use an Effect to fetch data for your component. Note that [if you use a framework,](https://react.dev/learn/creating-a-react-app#full-stack-frameworks) using your framework’s data fetching mechanism will be a lot more efficient than writing Effects manually.

If you want to fetch data from an Effect manually, your code might look like this:

```
import { useState, useEffect } from 'react';

import { fetchBio } from './api.js';

export default function Page() {

  const [person, setPerson] = useState('Alice');

  const [bio, setBio] = useState(null);

  useEffect(() => {

    let ignore = false;

    setBio(null);

    fetchBio(person).then(result => {

      if (!ignore) {

        setBio(result);

      }

    });

    return () => {

      ignore = true;

    };

  }, [person]);

  // ...
```
Note the `ignore` variable which is initialized to `false`, and is set to `true` during cleanup. This ensures [your code doesn’t suffer from “race conditions”:](https://maxrozen.com/race-conditions-fetching-data-react-with-useeffect) network responses may arrive in a different order than you sent them.

App.js

App.js

```
import { useState, useEffect } from 'react'; import { fetchBio } from './api.js'; export default function Page() {
  const [person, setPerson] = useState('Alice');
  const [bio, setBio] = useState(null);
  useEffect(() => {
