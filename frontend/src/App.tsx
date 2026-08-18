import Header from "./components/Header";
import { ToastProvider } from "./components/Toast";
import ProductDetailView from "./views/ProductDetailView";
import SearchView from "./views/SearchView";
import TrackedView from "./views/TrackedView";
import { useRoute } from "./useRoute";

export default function App() {
  const route = useRoute();

  let view;
  if (route.path === "/tracked") {
    view = <TrackedView />;
  } else if (route.path === "/products" && route.parts[1]) {
    view = <ProductDetailView id={Number(route.parts[1])} />;
  } else {
    view = <SearchView />;
  }

  return (
    <ToastProvider>
      <Header />
      {view}
    </ToastProvider>
  );
}
