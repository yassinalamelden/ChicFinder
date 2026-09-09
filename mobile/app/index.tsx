import { Redirect } from "expo-router";

/** The root layout's gate handles the real routing; this just picks a start. */
export default function Index() {
  return <Redirect href="/(tabs)/search" />;
}
