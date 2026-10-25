[API Reference](https://react.dev/reference/react)

[Hooks](https://react.dev/reference/react/hooks)

# useRef

`useRef` is a React Hook that lets you reference a value that’s not needed for rendering.

```
const ref = useRef(initialValue)
```
- [Reference ](https://react.dev/reference/react/useRef#reference)

    - [`useRef(initialValue)`](https://react.dev/reference/react/useRef#useref)

- [Usage ](https://react.dev/reference/react/useRef#usage)

    - [Referencing a value with a ref ](https://react.dev/reference/react/useRef#referencing-a-value-with-a-ref)

    - [Manipulating the DOM with a ref ](https://react.dev/reference/react/useRef#manipulating-the-dom-with-a-ref)

    - [Avoiding recreating the ref contents ](https://react.dev/reference/react/useRef#avoiding-recreating-the-ref-contents)

- [Troubleshooting ](https://react.dev/reference/react/useRef#troubleshooting)

    - [I can’t get a ref to a custom component ](https://react.dev/reference/react/useRef#i-cant-get-a-ref-to-a-custom-component)

## Reference 

### `useRef(initialValue)`

Call `useRef` at the top level of your component to declare a [ref.](https://react.dev/learn/referencing-values-with-refs)

```
import { useRef } from 'react';

function MyComponent() {

  const intervalRef = useRef(0);

  const inputRef = useRef(null);

  // ...
```
[See more examples below.](https://react.dev/reference/react/useRef#usage)

#### Parameters 

- `initialValue`: The value you want the ref object’s `current` property to be initially. It can be a value of any type. This argument is ignored after the initial render.

#### Returns 

`useRef` returns an object with a single property:

- `current`: Initially, it’s set to the `initialValue` you have passed. You can later set it to something else. If you pass the ref object to React as a `ref` attribute to a JSX node, React will set its `current` property.

On the next renders, `useRef` will return the same object.

#### Caveats 

- You can mutate the `ref.current` property. Unlike state, it is mutable. However, if it holds an object that is used for rendering (for example, a piece of your state), then you shouldn’t mutate that object.

- When you change the `ref.current` property, React does not re-render your component. React is not aware of when you change it because a ref is a plain JavaScript object.

- Do not write *or read* `ref.current` during rendering, except for [initialization.](https://react.dev/reference/react/useRef#avoiding-recreating-the-ref-contents) This makes your component’s behavior unpredictable.

- In Strict Mode, React will **call your component function twice**  in order to [help you find accidental impurities.](https://react.dev/reference/react/useState#my-initializer-or-updater-function-runs-twice) This is development-only behavior and does not affect production. Each ref object will be created twice, but one of the versions will be discarded. If your component function is pure (as it should be), this should not affect the behavior.

## Usage 

### Referencing a value with a ref 

Call `useRef` at the top level of your component to declare one or more [refs.](https://react.dev/learn/referencing-values-with-refs)

```
import { useRef } from 'react';

function Stopwatch() {

  const intervalRef = useRef(0);

  // ...
```
`useRef` returns a ref object with a single `current` property initially set to the initial value you provided.

On the next renders, `useRef` will return the same object. You can change its `current` property to store information and read it later. This might remind you of [state](https://react.dev/reference/react/useState), but there is an important difference.

**Changing a ref does not trigger a re-render.**  This means refs are perfect for storing information that doesn’t affect the visual output of your component. For example, if you need to store an [interval ID](https://developer.mozilla.org/en-US/docs/Web/API/setInterval) and retrieve it later, you can put it in a ref. To update the value inside the ref, you need to manually change its `current` property:

```
function handleStartClick() {

  const intervalId = setInterval(() => {

    // ...

  }, 1000);

  intervalRef.current = intervalId;

}
```
Later, you can read that interval ID from the ref so that you can call [clear that interval](https://developer.mozilla.org/en-US/docs/Web/API/clearInterval):

```
function handleStopClick() {

  const intervalId = intervalRef.current;

  clearInterval(intervalId);

}
```
By using a ref, you ensure that:

- You can **store information**  between re-renders (unlike regular variables, which reset on every render).

- Changing it **does not trigger a re-render**  (unlike state variables, which trigger a re-render).

- The **information is local**  to each copy of your component (unlike the variables outside, which are shared).

Changing a ref does not trigger a re-render, so refs are not appropriate for storing information you want to display on the screen. Use state for that instead. Read more about [choosing between `useRef` and `useState`.](https://react.dev/learn/referencing-values-with-refs#differences-between-refs-and-state)

#### Examples of referencing a value with useRef

1. Click counter 2. A stopwatch 

#### 
Example 1 of 2: Click counter 

This component uses a ref to keep track of how many times the button was clicked. Note that it’s okay to use a ref instead of state here because the click count is only read and written in an event handler.

App.js

App.js

 Download

```
import { useRef } from 'react'; export default function Counter() {
  let ref = useRef(0);

  function handleClick() {
    ref.current = ref.current + 1;
    alert('You clicked ' + ref.current + ' times!');
  }

  return (
    <button onClick={handleClick}>
 Click me!
 </button>
  ); } 
```
If you show `{ref.current}` in the JSX, the number won’t update on click. This is because setting `ref.current` does not trigger a re-render. Information that’s used for rendering should be state instead.

Next Example

### Pitfall

**Do not write *or read* `ref.current` during rendering.**

React expects that the body of your component [behaves like a pure function](https://react.dev/learn/keeping-components-pure):

- If the inputs ([props](https://react.dev/learn/passing-props-to-a-component), [state](https://react.dev/learn/state-a-components-memory), and [context](https://react.dev/learn/passing-data-deeply-with-context)) are the same, it should return exactly the same JSX.

- Calling it in a different order or with different arguments should not affect the results of other calls.

Reading or writing a ref **during rendering**  breaks these expectations.

```
function MyComponent() {

  // ...

  // 🚩 Don't write a ref during rendering

  myRef.current = 123;

  // ...

  // 🚩 Don't read a ref during rendering

  return <h1>{myOtherRef.current}</h1>;

}
```
You can read or write refs **from event handlers or effects instead** .

```
function MyComponent() {

  // ...

  useEffect(() => {

    // ✅ You can read or write refs in effects

    myRef.current = 123;

  });

  // ...

  function handleClick() {

    // ✅ You can read or write refs in event handlers

    doSomething(myOtherRef.current);

  }

  // ...

}
```
If you *have to* read [or write](https://react.dev/reference/react/useState#storing-information-from-previous-renders) something during rendering, [use state](https://react.dev/reference/react/useState) instead.

When you break these rules, your component might still work, but most of the newer features we’re adding to React will rely on these expectations. Read more about [keeping your components pure.](https://react.dev/learn/keeping-components-pure#where-you-_can_-cause-side-effects)

### Manipulating the DOM with a ref 

It’s particularly common to use a ref to manipulate the [DOM.](https://developer.mozilla.org/en-US/docs/Web/API/HTML_DOM_API) React has built-in support for this.

First, declare a ref object with an initial value of `null`:

```
import { useRef } from 'react';

function MyComponent() {

  const inputRef = useRef(null);

  // ...
```
Then pass your ref object as the `ref` attribute to the JSX of the DOM node you want to manipulate:

```
  // ...

  return <input ref={inputRef} />;
```
After React creates the DOM node and puts it on the screen, React will set the `current` property of your ref object to that DOM node. Now you can access the `<input>`’s DOM node and call methods like [`focus()`](https://developer.mozilla.org/en-US/docs/Web/API/HTMLElement/focus):

```
  function handleClick() {

    inputRef.current.focus();

  }
```
React will set the `current` property back to `null` when the node is removed from the screen.

Read more about [manipulating the DOM with refs.](https://react.dev/learn/manipulating-the-dom-with-refs)

#### Examples of manipulating the DOM with useRef

1. Focusing a text input 2. Scrolling an image into view 3. Playing and pausing a video 4. Exposing a ref to your own component 

#### 
Example 1 of 4: Focusing a text input 

In this example, clicking the button will focus the input:

App.js

App.js

 Download

```
import { useRef } from 'react'; export default function Form() {
  const inputRef = useRef(null);

  function handleClick() {
    inputRef.current.focus();
  }

  return (
    <>
      <input ref={inputRef} />
      <button onClick={handleClick}>
 Focus the input
 </button>
    </>
  ); } 
```
Next Example

### Avoiding recreating the ref contents 

React saves the initial ref value once and ignores it on the next renders.

```
function Video() {

  const playerRef = useRef(new VideoPlayer());

  // ...
```
Although the result of `new VideoPlayer()` is only used for the initial render, you’re still calling this function on every render. This can be wasteful if it’s creating expensive objects.

To solve it, you may initialize the ref like this instead:

```
function Video() {

  const playerRef = useRef(null);

  if (playerRef.current === null) {

    playerRef.current = new VideoPlayer();

  }

  // ...
```
Normally, writing or reading `ref.current` during render is not allowed. However, it’s fine in this case because the result is always the same, and the condition only executes during initialization so it’s fully predictable.

Details

##### 
Deep Dive

#### How to avoid null checks when initializing useRef later 

If you use a type checker and don’t want to always check for `null`, you can try a pattern like this instead:

```
function Video() {

  const playerRef = useRef(null);

  function getPlayer() {

    if (playerRef.current !== null) {

      return playerRef.current;

    }

    const player = new VideoPlayer();

    playerRef.current = player;

    return player;

  }

  // ...
```
Here, the `playerRef` itself is nullable. However, you should be able to convince your type checker that there is no case in which `getPlayer()` returns `null`. Then use `getPlayer()` in your event handlers.

## Troubleshooting 

### I can’t get a ref to a custom component 

If you try to pass a `ref` to your own component like this:

```
const inputRef = useRef(null);

return <MyInput ref={inputRef} />;
```
You might get an error in the console:

Console

TypeError: Cannot read properties of null

By default, your own components don’t expose refs to the DOM nodes inside them.

To fix this, find the component that you want to get a ref to:

```
export default function MyInput({ value, onChange }) {

  return (

    <input

      value={value}

      onChange={onChange}

    />

  );

}
```
And then add `ref` to the list of props your component accepts and pass `ref` as a prop to the relevant child [built-in component](https://react.dev/reference/react-dom/components/common) like this:

```
function MyInput({ value, onChange, ref }) {

  return (

    <input

      value={value}

      onChange={onChange}

      ref={ref}

    />

  );

};

export default MyInput;
```
Then the parent component can get a ref to it.

Read more about [accessing another component’s DOM nodes.](https://react.dev/learn/manipulating-the-dom-with-refs#accessing-another-components-dom-nodes)

[PrevioususeReducer](https://react.dev/reference/react/useReducer)

[NextuseState](https://react.dev/reference/react/useState)

## On this page

- [Overview](https://react.dev/reference/react/useRef#)

- [Reference ](https://react.dev/reference/react/useRef#reference)

- [`useRef(initialValue)`](https://react.dev/reference/react/useRef#useref)

- [Usage ](https://react.dev/reference/react/useRef#usage)

- [Referencing a value with a ref ](https://react.dev/reference/react/useRef#referencing-a-value-with-a-ref)

- [Manipulating the DOM with a ref ](https://react.dev/reference/react/useRef#manipulating-the-dom-with-a-ref)

- [Avoiding recreating the ref contents ](https://react.dev/reference/react/useRef#avoiding-recreating-the-ref-contents)

- [Troubleshooting ](https://react.dev/reference/react/useRef#troubleshooting)

- [I can’t get a ref to a custom component ](https://react.dev/reference/react/useRef#i-cant-get-a-ref-to-a-custom-component)